import datetime
import demjson
import numpy as np
import re
from sqlalchemy import desc
from ScrapyKeeper.app import db, Base


class Project(Base):
    __tablename__ = 'sk_project'

    project_name = db.Column(db.String(50))

    @classmethod
    def load_project(cls, project_list):
        for project in project_list:
            existed_project = cls.query.filter_by(project_name=project.project_name).first()
            if not existed_project:
                try:
                    db.session.add(project)
                    db.session.commit()
                except:
                    db.session.rollback()
                    raise

    @classmethod
    def find_project_by_id(cls, project_id):
        return Project.query.filter_by(id=project_id).first()

    def to_dict(self):
        return {
            "project_id": self.id,
            "project_name": self.project_name
        }


class SpiderInstance(Base):
    __tablename__ = 'sk_spider'

    spider_name = db.Column(db.String(100))
    project_id = db.Column(db.INTEGER, nullable=False, index=True)

    @classmethod
    def update_spider_instances(cls, project_id, spider_instance_list):
        for spider_instance in spider_instance_list:
            existed_spider_instance = cls.query.filter_by(project_id=project_id,
                                                          spider_name=spider_instance.spider_name).first()
            if not existed_spider_instance:
                try:
                    db.session.add(spider_instance)
                    db.session.commit()
                except:
                    db.session.rollback()
                    raise

        for spider in cls.query.filter_by(project_id=project_id).all():
            existed_spider = any(
                spider.spider_name == s.spider_name
                for s in spider_instance_list
            )
            if not existed_spider:
                try:
                    db.session.delete(spider)
                    db.session.commit()
                except:
                    db.session.rollback()
                    raise

    @classmethod
    def list_spider_by_project_id(cls, project_id):
        return cls.query.filter_by(project_id=project_id).all()

    def to_dict(self):
        return dict(spider_instance_id=self.id,
                    spider_name=self.spider_name,
                    project_id=self.project_id)

    @classmethod
    def list_spiders(cls, project_id):
        sql_last_runtime = '''
            select * from (select a.spider_name,b.date_created from sk_job_instance as a
                left join sk_job_execution as b
                on a.id = b.job_instance_id
                order by b.date_created desc) as c
                group by c.spider_name
            '''
        sql_avg_runtime = '''
            select a.spider_name,avg(end_time-start_time) from sk_job_instance as a
                left join sk_job_execution as b
                on a.id = b.job_instance_id
                where b.end_time is not null
                group by a.spider_name
            '''
        last_runtime_list = dict(
            (spider_name, last_run_time) for spider_name, last_run_time in db.engine.execute(sql_last_runtime))
        avg_runtime_list = dict(
            (spider_name, avg_run_time) for spider_name, avg_run_time in db.engine.execute(sql_avg_runtime))
        res = []
        for spider in cls.query.filter_by(project_id=project_id).all():
            last_runtime = last_runtime_list.get(spider.spider_name)
            res.append(dict(spider.to_dict(),
                            **{'spider_last_runtime': last_runtime if last_runtime else '-',
                               'spider_avg_runtime': avg_runtime_list.get(spider.spider_name)
                               }))
        return res


class JobPriority():
    LOW, NORMAL, HIGH, HIGHEST = range(-1, 3)


class JobRunType():
    ONETIME = 'onetime'
    PERIODIC = 'periodic'


class JobInstance(Base):
    __tablename__ = 'sk_job_instance'

    spider_name = db.Column(db.String(100), nullable=False, index=True)
    project_id = db.Column(db.INTEGER, nullable=False, index=True)
    tags = db.Column(db.Text)  # job tag(split by , )
    spider_arguments = db.Column(db.Text)  # job execute arguments(split by , ex.: arg1=foo,arg2=bar)
    priority = db.Column(db.INTEGER)
    desc = db.Column(db.Text)
    cron_minutes = db.Column(db.String(20), default="0")
    cron_hour = db.Column(db.String(20), default="*")
    cron_day_of_month = db.Column(db.String(20), default="*")
    cron_day_of_week = db.Column(db.String(20), default="*")
    cron_month = db.Column(db.String(20), default="*")
    enabled = db.Column(db.INTEGER, default=0)  # 0/-1
    run_type = db.Column(db.String(20))  # periodic/onetime

    def to_dict(self):
        return dict(
            job_instance_id=self.id,
            spider_name=self.spider_name,
            tags=self.tags.split(',') if self.tags else None,
            spider_arguments=self.spider_arguments,
            priority=self.priority,
            desc=self.desc,
            cron_minutes=self.cron_minutes,
            cron_hour=self.cron_hour,
            cron_day_of_month=self.cron_day_of_month,
            cron_day_of_week=self.cron_day_of_week,
            cron_month=self.cron_month,
            enabled=self.enabled == 0,
            run_type=self.run_type

        )

    @classmethod
    def list_job_instance_by_project_id(cls, project_id):
        return cls.query.filter_by(project_id=project_id).all()

    @classmethod
    def find_job_instance_by_id(cls, job_instance_id):
        return cls.query.filter_by(id=job_instance_id).first()


class SpiderStatus():
    PENDING, RUNNING, FINISHED, CANCELED = range(4)


class JobExecution(Base):
    __tablename__ = 'sk_job_execution'

    project_id = db.Column(db.INTEGER, nullable=False, index=True)
    service_job_execution_id = db.Column(db.String(50), nullable=False, index=True)
    job_instance_id = db.Column(db.INTEGER, nullable=False, index=True)
    create_time = db.Column(db.DateTime)
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    running_status = db.Column(db.INTEGER, default=SpiderStatus.PENDING)
    running_on = db.Column(db.Text)

    raw_stats = db.Column(db.Text)
    requests_count = db.Column(db.Integer, default=0)
    items_count = db.Column(db.Integer, default=0)
    warnings_count = db.Column(db.Integer, default=0)
    errors_count = db.Column(db.Integer, default=0)
    bytes_count = db.Column(db.Integer, default=0)
    retries_count = db.Column(db.Integer, default=0)
    exceptions_count = db.Column(db.Integer, default=0)
    cache_size_count = db.Column(db.Integer, default=0)
    cache_object_count = db.Column(db.Integer, default=0)
    RAW_STATS_REGEX = '\[scrapy\.statscollectors\][^{]+({[^}]+})'
    def process_raw_stats(self):
        if self.raw_stats is None:
            return
        datetime_regex = '(datetime\.datetime\([^)]+\))'
        self.raw_stats = re.sub(datetime_regex, r"'\1'", self.raw_stats)
        stats = demjson.decode(self.raw_stats)
        self.requests_count = stats.get('downloader/request_count') or 0
        self.items_count = stats.get('item_scraped_count') or 0
        self.warnings_count = stats.get('log_count/WARNING') or 0
        self.errors_count = stats.get('log_count/ERROR') or 0
        self.bytes_count = stats.get('downloader/response_bytes') or 0
        self.retries_count = stats.get('retry/count') or 0
        self.exceptions_count = stats.get('downloader/exception_count') or 0
        self.cache_size_count = stats.get('cache/size/end') or 0
        self.cache_object_count = stats.get('cache/object/keeped') or 0
    def has_warnings(self):
        return not self.raw_stats or not self.items_count or self.warnings_count
    def has_errors(self):
        return bool(self.errors_count)

    def to_dict(self):
        job_instance = JobInstance.query.filter_by(id=self.job_instance_id).first()
        return {
            'project_id': self.project_id,
            'job_execution_id': self.id,
            'job_instance_id': self.job_instance_id,
            'service_job_execution_id': self.service_job_execution_id,
            'create_time': self.create_time.strftime('%Y-%m-%d %H:%M:%S') if self.create_time else None,
            'start_time': self.start_time.strftime('%Y-%m-%d %H:%M:%S') if self.start_time else None,
            'end_time': self.end_time.strftime('%Y-%m-%d %H:%M:%S') if self.end_time else None,
            'running_status': self.running_status,
            'running_on': self.running_on,
            'job_instance': job_instance.to_dict() if job_instance else {},
            'has_warnings': self.has_warnings(),
            'has_errors': self.has_errors(),
            'requests_count': self.requests_count if self.requests_count is not None else 0,
            'items_count': self.items_count if self.items_count is not None else 0,
            'warnings_count': self.warnings_count if self.warnings_count is not None else 0,
            'errors_count': self.errors_count if self.errors_count is not None else 0,
            'bytes_count': self.bytes_count if self.bytes_count is not None else 0,
            'retries_count': self.retries_count if self.retries_count is not None else 0,
            'exceptions_count': self.exceptions_count if self.exceptions_count is not None else 0,
            'cache_size_count': self.cache_size_count if self.cache_size_count is not None else 0,
            'cache_object_count': self.cache_object_count if self.cache_object_count is not None else 0
        }

    @classmethod
    def find_job_by_service_id(cls, service_job_execution_id):
        return cls.query.filter_by(service_job_execution_id=service_job_execution_id).first()

    @classmethod
    def list_job_by_service_ids(cls, service_job_execution_ids):
        return cls.query.filter(cls.service_job_execution_id.in_(service_job_execution_ids)).all()

    @classmethod
    def list_uncomplete_job(cls):
        return cls.query.filter(cls.running_status != SpiderStatus.FINISHED,
                                cls.running_status != SpiderStatus.CANCELED).all()

    @classmethod
    def list_jobs(cls, project_id, each_status_limit=100):
        result = {}
        result['PENDING'] = [job_execution.to_dict() for job_execution in
                             JobExecution.query.filter_by(project_id=project_id,
                                                          running_status=SpiderStatus.PENDING).order_by(
                                 desc(JobExecution.date_modified)).limit(each_status_limit)]
        result['RUNNING'] = [job_execution.to_dict() for job_execution in
                             JobExecution.query.filter_by(project_id=project_id,
                                                          running_status=SpiderStatus.RUNNING).order_by(
                                 desc(JobExecution.date_modified)).limit(each_status_limit)]
        result['COMPLETED'] = [job_execution.to_dict() for job_execution in
                               JobExecution.query.filter(JobExecution.project_id == project_id).filter(
                                   (JobExecution.running_status == SpiderStatus.FINISHED) | (
                                       JobExecution.running_status == SpiderStatus.CANCELED)).order_by(
                                   desc(JobExecution.date_modified)).limit(each_status_limit)]
        return result

    @classmethod
    def list_working_time(cls, project_id):
        result = {}
        last_time = datetime.datetime.now() - datetime.timedelta(hours=23)
        last_time = datetime.datetime(last_time.year, last_time.month, last_time.day, last_time.hour)
        for job_execution in JobExecution.query.filter(JobExecution.project_id == project_id,
                                                       JobExecution.date_created >= last_time).all():
            if (job_execution.start_time != None) : # avoid unstarted jobs
                if job_execution.end_time == None:  # treat unfinished jobs
                    duration = (datetime.datetime.now() - job_execution.start_time).total_seconds()
                else :                              # normal case
                    duration = (job_execution.end_time - job_execution.start_time).total_seconds()
                dico = job_execution.to_dict()
                if dico['job_instance'] != {}:
                    if dico['job_instance']['spider_name'] in result.keys():
                        result[dico['job_instance']['spider_name']] += duration
                    else :
                        result[dico['job_instance']['spider_name']] = duration
        result_sorted = {}
        for key in sorted(result.keys()): result_sorted[key] = result[key]
        return result_sorted

    @classmethod
    def list_last_run(cls, project_id):
        result = []
        for job_execution in JobExecution.query.filter_by(project_id=project_id).order_by(desc(JobExecution.id)).limit(15).all():
            result.append(job_execution.to_dict())
        result.reverse()
        return result

    @classmethod
    def list_quality_review(cls, project_id):
        result = {}
        iteration = {}
        for job_execution in JobExecution.query.filter_by(project_id=project_id).order_by(desc(JobExecution.id)).limit(100).all():
            
            dico = job_execution.to_dict()
            # Errors, Retry, Exceptions, Bytes, Cache Size
            stream = np.array([ dico['errors_count'], dico['retries_count'], dico['exceptions_count'],
                                dico['warnings_count'], dico['bytes_count'], dico['cache_size_count'] ])
            if dico['job_instance'] != {}:
                if dico['job_instance']['spider_name'] in result.keys():
                    if iteration[dico['job_instance']['spider_name']] < 10 :
                        iteration[dico['job_instance']['spider_name']] += 1
                        result[dico['job_instance']['spider_name']] += stream
                else :
                    iteration[dico['job_instance']['spider_name']] = 1
                    result[dico['job_instance']['spider_name']] = stream
        total = np.array([.01, .01, .01, .01, .01, .01])
        # average ratio
        for i in result.keys():
            result[i] = np.array(result[i]) / np.array([1, 1, 1, 1, iteration[i], iteration[i]])
            total += np.array(result[i])
        # compare ratio
        for i in result.keys():
            result[i] = np.array(result[i]) / total
        return result

    @classmethod
    def list_last_ee(cls, project_id):
        result = []
        for job_execution in JobExecution.query.filter(JobExecution.project_id == project_id).filter(
                                    (JobExecution.errors_count >= 1) | (JobExecution.exceptions_count >= 1) | (JobExecution.items_count == 0)
                                    ).order_by(desc(JobExecution.id)).limit(10).all():
            result.append(job_execution.to_dict())
        return result

    @classmethod
    def list_run_stats_by_hours(cls, project_id):
        result = {}
        hour_keys = []
        last_time = datetime.datetime.now() - datetime.timedelta(hours=23)
        last_time = datetime.datetime(last_time.year, last_time.month, last_time.day, last_time.hour)
        for hour in range(23, -1, -1):
            time_tmp = datetime.datetime.now() - datetime.timedelta(hours=hour)
            hour_key = time_tmp.strftime('%Y-%m-%d %H:00:00')
            hour_keys.append(hour_key)
            result[hour_key] = 0  # init
        for job_execution in JobExecution.query.filter(JobExecution.project_id == project_id,
                                                       JobExecution.date_created >= last_time).all():
            hour_key = job_execution.create_time.strftime('%Y-%m-%d %H:00:00')
            result[hour_key] += job_execution.items_count
        return [dict(key=hour_key, value=result[hour_key]) for hour_key in hour_keys]

    @classmethod
    def list_spider_stats(cls, project_id, spider_id):
        result = []
        for spider in SpiderInstance.query.filter_by(project_id=project_id, id=spider_id).all():
            spider_name = spider.spider_name
        job_instances = []
        for job_instance in JobInstance.query.filter_by(spider_name=spider_name).order_by(desc(JobInstance.id)).limit(10).all():
            job_instances.append(job_instance.id)
        for job_execution in JobExecution.query.filter(JobExecution.job_instance_id.in_(job_instances)).order_by(desc(JobExecution.id)).all() :
            result.append(job_execution.to_dict())
        result.reverse()
        return result

    @classmethod
    def list_request_stats_by_hours(cls, project_id, spider_id):
        result = {}
        hour_keys = []
        last_time = datetime.datetime.now() - datetime.timedelta(hours=23)
        last_time = datetime.datetime(last_time.year, last_time.month, last_time.day, last_time.hour)
        for hour in range(23, -1, -1):
            time_tmp = datetime.datetime.now() - datetime.timedelta(hours=hour)
            hour_key = time_tmp.strftime('%Y-%m-%d %H:00:00')
            hour_keys.append(hour_key)
            result[hour_key] = 0  # init
        if spider_id == "project" :
            for job_execution in JobExecution.query.filter(JobExecution.project_id == project_id,
                                                       JobExecution.date_created >= last_time).all():
                hour_key = job_execution.create_time.strftime('%Y-%m-%d %H:00:00')
                result[hour_key] += job_execution.requests_count
        else :
            for job_execution in JobExecution.query.filter(JobExecution.project_id == project_id,
                                                       JobExecution.job_instance_id == spider_id,
                                                       JobExecution.date_created >= last_time).all():
                hour_key = job_execution.create_time.strftime('%Y-%m-%d %H:00:00')
                result[hour_key] += job_execution.requests_count
        return [dict(key=hour_key, value=result[hour_key]) for hour_key in hour_keys]

    @classmethod
    def list_item_stats_by_hours(cls, project_id, spider_id):
        result = {}
        hour_keys = []
        last_time = datetime.datetime.now() - datetime.timedelta(hours=23)
        last_time = datetime.datetime(last_time.year, last_time.month, last_time.day, last_time.hour)
        for hour in range(23, -1, -1):
            time_tmp = datetime.datetime.now() - datetime.timedelta(hours=hour)
            hour_key = time_tmp.strftime('%Y-%m-%d %H:00:00')
            hour_keys.append(hour_key)
            result[hour_key] = 0  # init
        if spider_id == "project" :
            for job_execution in JobExecution.query.filter(JobExecution.project_id == project_id,
                                                       JobExecution.date_created >= last_time).all():
                hour_key = job_execution.create_time.strftime('%Y-%m-%d %H:00:00')
                result[hour_key] += job_execution.items_count
        else :
            for job_execution in JobExecution.query.filter(JobExecution.project_id == project_id,
                                                       JobExecution.job_instance_id == spider_id,
                                                       JobExecution.date_created >= last_time).all():
                hour_key = job_execution.create_time.strftime('%Y-%m-%d %H:00:00')
                result[hour_key] += job_execution.items_count
        return [dict(key=hour_key, value=result[hour_key]) for hour_key in hour_keys]
