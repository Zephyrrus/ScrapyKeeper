import time
from datetime import datetime, timedelta
from sqlalchemy import func, or_
from ScrapyKeeper import config
from ScrapyKeeper.app import scheduler, app, agent, JobExecution, db, SpiderSetup
from ScrapyKeeper.app.spider.model import Project, JobInstance, SpiderInstance, JobRunType, JobPriority, SpiderStatus
from ScrapyKeeper.app.util.cluster import cluster_has_enough_free_memory



def sync_job_execution_status_job():
    """
    sync job execution running status
    :return:
    """
    for project in Project.query.all():
        agent.sync_job_status(project)
    app.logger.debug('[sync_job_execution_status]')


def sync_spiders():
    """
    sync spiders
    :return:
    """
    for project in Project.query.all():
        spider_instance_list = agent.get_spider_list(project)
        SpiderInstance.update_spider_instances(project.id, spider_instance_list)
    app.logger.debug('[sync_spiders]')


def run_spider_job(job_instance_id):
    """
    run spider by scheduler
    :param job_instance_id:
    :return:
    """
    try:
        job_instance = JobInstance.find_job_instance_by_id(job_instance_id)
        agent.start_spider(job_instance)
        app.logger.info('[run_spider_job][project:%s][spider_name:%s][job_instance_id:%s]' % (
            job_instance.project_id, job_instance.spider_name, job_instance.id))
    except Exception as e:
        app.logger.error('[run_spider_job] ' + str(e))


def reload_runnable_spider_job_execution():
    """
    add periodic job to scheduler
    :return:
    """
    running_job_ids = set([job.id for job in scheduler.get_jobs()])
    # app.logger.debug('[running_job_ids] %s' % ','.join(running_job_ids))
    available_job_ids = set()
    # add new job to schedule
    for job_instance in JobInstance.query.filter_by(enabled=0, run_type="periodic").all():
        job_id = "spider_job_%s:%s" % (job_instance.id, int(time.mktime(job_instance.date_modified.timetuple())))
        available_job_ids.add(job_id)
        if job_id not in running_job_ids:
            try:
                scheduler.add_job(run_spider_job,
                                  args=(job_instance.id,),
                                  trigger='cron',
                                  id=job_id,
                                  minute=job_instance.cron_minutes,
                                  hour=job_instance.cron_hour,
                                  day=job_instance.cron_day_of_month,
                                  day_of_week=job_instance.cron_day_of_week,
                                  month=job_instance.cron_month,
                                  second=0,
                                  max_instances=999,
                                  misfire_grace_time=60 * 60,
                                  coalesce=True)
            except Exception as e:
                app.logger.error(
                    '[load_spider_job] failed {} {},may be cron expression format error '.format(job_id, str(e)))
            app.logger.info('[load_spider_job][project:%s][spider_name:%s][job_instance_id:%s][job_id:%s]' % (
                job_instance.project_id, job_instance.spider_name, job_instance.id, job_id))
    # remove invalid jobs
    for invalid_job_id in filter(lambda job_id: job_id.startswith("spider_job_"),
                                 running_job_ids.difference(available_job_ids)):
        scheduler.remove_job(invalid_job_id)
        app.logger.info('[drop_spider_job][job_id:%s]' % invalid_job_id)

    app.logger.debug('[reload_runnable_spider_job_execution]')


def run_spiders_dynamically():
    """
    Run all the spiders when needed
    :return:
    """
    if not config.AUTO_SCHEDULE_ENABLED:
        return

    for project in Project.query.all():
        _run_spiders_for_project(project)

    app.logger.debug('[run_spiders_dynamically]')


def _run_spiders_for_project(project: Project):
    """
    Run all the spiders for the current project
    :param project:
    :return:
    """
    started_spiders = 0

    # grab the list with all the spiders in the project
    spiders_list_by_last_run = SpiderInstance.query \
           .with_entities(SpiderInstance.id, SpiderInstance.spider_name, func.max(JobExecution.start_time)) \
           .outerjoin(JobInstance, (JobInstance.spider_name == SpiderInstance.spider_name) & (
                   JobInstance.project_id == SpiderInstance.project_id)) \
           .outerjoin(JobExecution, JobExecution.job_instance_id == JobInstance.id) \
           .filter(or_(
                JobExecution.running_status == SpiderStatus.FINISHED, JobInstance.id.is_(None),
                JobExecution.running_status != SpiderStatus.FINISHED
            )) \
           .group_by(SpiderInstance.id) \
           .order_by(func.max(JobExecution.start_time)) \
           .all()

    # compute the current running load
    current_run_load = _get_current_run_load(project.id)

    # run the spiders that we have to run
    for spider_to_run in spiders_list_by_last_run:
        if started_spiders >= config.MAX_SPIDERS_START_AT_ONCE:
            return

        spider_avg_load = _get_spider_average_run_stats(project.id, spider_to_run.id)
        spider_avg_load = spider_avg_load or config.DEFAULT_AUTOTHROTTLE_MAX_CONCURRENCY

        if _spider_should_run(spider_to_run.id, spider_avg_load, current_run_load):
            _run_spider(spider_to_run.spider_name, project.id)
            started_spiders += 1
            current_run_load += spider_avg_load

        if current_run_load >= config.MAX_LOAD_ALLOWED:
            # the load is already to the max, we can't add anything
            return


def _get_current_run_load(project_id) -> float:
    """
    Get the current work load for all the jobs
    :param project_id:
    :return:
    """
    running_jobs = JobExecution.list_running_jobs(project_id)

    current_jobs_load = [running_job['job_instance']['throttle_concurrency'] for running_job in running_jobs]
    total_load = sum(current_jobs_load)

    return total_load


def _get_spider_average_run_stats(project_id, spider_id) -> float:
    # grab only execution that finished successfully
    execution_list = JobExecution.list_spider_stats(project_id, spider_id)
    # filter those runs that have finished "successfully" but without having any statistic
    execution_list = [job_execution for job_execution in execution_list if job_execution['requests_count']]
    # keep only the latest 10 runs
    execution_list = execution_list[-10:]

    requests_counters = [execution['job_instance']['throttle_concurrency'] for execution in execution_list
                         if execution['job_instance']['throttle_concurrency'] is not None]
    average_load = sum(requests_counters) / max(len(requests_counters), 1)

    return average_load


def _run_spider(spider_name, project_id):
    """
    Run a spider
    :param spider_name:
    :param project_id:
    :return:
    """
    job_instance = JobInstance()
    job_instance.project_id = project_id
    job_instance.spider_name = spider_name
    job_instance.priority = JobPriority.NORMAL
    job_instance.run_type = JobRunType.ONETIME
    job_instance.overlapping = True
    job_instance.enabled = -1

    # settings for tempering the requests
    throttle_value = _get_throttle_value(spider_name, project_id)
    job_instance.spider_arguments = "setting=AUTOTHROTTLE_TARGET_CONCURRENCY={}".format(throttle_value)
    job_instance.throttle_concurrency = throttle_value

    db.session.add(job_instance)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e

    agent.start_spider(job_instance)


def _get_throttle_value(spider_name, project_id):
    """
    Find the AUTOTHROTTLE_TARGET_CONCURRENCY for this request
    :param spider_name:
    :param project_id:
    :return:
    """
    spider_instance = SpiderInstance.query.filter_by(spider_name=spider_name, project_id=project_id).first()

    # grab only execution that finished successfully
    execution_list = JobExecution.list_spider_stats(project_id, spider_instance.id)
    # keep only the latest 10 runs
    execution_list = execution_list[-10:]

    execution_seconds = [(datetime.strptime(execution['end_time'], '%Y-%m-%d %H:%M:%S')
                          - datetime.strptime(execution['start_time'], '%Y-%m-%d %H:%M:%S')).total_seconds()
                         for execution in execution_list]
    # get average run time in minutes
    average_mins = sum(execution_seconds) / max(len(execution_seconds), 1) / 60

    if average_mins == 0:
        # when we don't have any info about past runs
        return config.DEFAULT_AUTOTHROTTLE_MAX_CONCURRENCY

    time_spent_ratio = float(1440 / average_mins)  # the ratio reported to 1 day
    # now we'll have to only keep the number with a min of .5 and a max of 10
    time_spent_ratio = max(time_spent_ratio, config.MIN_LOAD_RATIO_MULTIPLIER)
    time_spent_ratio = min(time_spent_ratio, config.MAX_LOAD_RATIO_MULTIPLIER)
    autothrottle_to_set = round(config.DEFAULT_AUTOTHROTTLE_MAX_CONCURRENCY / time_spent_ratio, 1)

    return autothrottle_to_set


def _spider_should_run(spider_id, spider_avg_load, current_run_load):
    """
    Check if this spider should run now
    :param spider_id:
    :param current_run_load:
    :return:
    """
    spider = SpiderInstance.query.get(spider_id)
    spider_setup = SpiderSetup.get_spider_setup(spider)
    last_run = JobExecution.get_last_spider_execution(spider.id, spider.project_id)

    if not _spider_should_run_today(spider, last_run):
        # test the crawler didn't run today (or in the last week for sellers)
        return False

    pending_instances = JobExecution.get_pending_jobs_by_spider_name(spider.spider_name, spider.project_id)
    if len(pending_instances):
        # check that another instance of the same crawler is in pending
        return False

    running_instances = JobExecution.get_running_jobs_by_spider_name(spider.spider_name, spider.project_id)
    if len(running_instances):
        # check that another instance of the same crawler is running
        return False

    if spider_setup.auto_schedule is False:
        # check if the marker from the DB allows auto scheduling
        return False

    if current_run_load + spider_avg_load > config.MAX_LOAD_ALLOWED:
        # check that the load is still under control
        return False

    if not cluster_has_enough_free_memory(app):
        # check if we have enough memory to run the spiders
        return False

    return True


def _spider_should_run_today(spider, last_run):
    """
    Check if the spider is allowed to run today
    :param spider:
    :param last_run:
    :return:
    """
    if 'sellers.' in spider.spider_name:
        # sellers should only run once a week
        reference_time = datetime.today().replace(hour=0, minute=0, second=0) - timedelta(days=7)
    else:
        # if is not a seller it should run if it didn't run today
        reference_time = datetime.today().replace(hour=0, minute=0, second=0)

    if last_run is not None and last_run > reference_time:
        return False

    return True
