import datetime
import os
import tempfile

import flask_restful
import requests
from flask import Blueprint, request
from flask import abort
from flask import flash
from flask import redirect
from flask import render_template
from flask import session
from flask_restful_swagger import swagger
from werkzeug.utils import secure_filename

from ScrapyKeeper import config
from ScrapyKeeper.app import db, api, agent, app, SpiderSetup
from ScrapyKeeper.app.spider import helper
from ScrapyKeeper.app.spider.model import JobInstance, Project, JobExecution, SpiderInstance, JobRunType

api_spider_bp = Blueprint('spider', __name__)

'''
========= api =========
'''


class ProjectCtrl(flask_restful.Resource):
    @swagger.operation(
        summary='list projects',
        parameters=[])
    def get(self):
        return [project.to_dict() for project in Project.query.all()]

    @swagger.operation(
        summary='add project',
        parameters=[{
            "name": "project_name",
            "description": "project name",
            "required": True,
            "paramType": "form",
            "dataType": 'string'
        }])
    def post(self):
        project_name = request.form['project_name']
        project = Project()
        project.project_name = project_name
        db.session.add(project)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e

        return project.to_dict()


class SpiderCtrl(flask_restful.Resource):
    @swagger.operation(
        summary='list spiders',
        parameters=[{
            "name": "project_id",
            "description": "project id",
            "required": True,
            "paramType": "path",
            "dataType": 'int'
        }])
    def get(self, project_id):
        project = Project.find_project_by_id(project_id)
        return [spider_instance.to_dict() for spider_instance in
                SpiderInstance.query.filter_by(project_id=project_id).all()]


class SpiderDetailCtrl(flask_restful.Resource):
    @swagger.operation(
        summary='spider detail',
        parameters=[{
            "name": "project_id",
            "description": "project id",
            "required": True,
            "paramType": "path",
            "dataType": 'int'
        }, {
            "name": "spider_id",
            "description": "spider instance id",
            "required": True,
            "paramType": "path",
            "dataType": 'int'
        }])
    def get(self, project_id, spider_id):
        spider_instance = SpiderInstance.query.filter_by(project_id=project_id, id=spider_id).first()
        return spider_instance.to_dict() if spider_instance else abort(404)

    @swagger.operation(
        summary='run spider',
        parameters=[{
            "name": "project_id",
            "description": "project id",
            "required": True,
            "paramType": "path",
            "dataType": 'int'
        }, {
            "name": "spider_id",
            "description": "spider instance id",
            "required": True,
            "paramType": "path",
            "dataType": 'int'
        }, {
            "name": "spider_arguments",
            "description": "spider arguments",
            "required": False,
            "paramType": "form",
            "dataType": 'string'
        }, {
            "name": "priority",
            "description": "LOW: -1, NORMAL: 0, HIGH: 1, HIGHEST: 2",
            "required": False,
            "paramType": "form",
            "dataType": 'int'
        }, {
            "name": "tags",
            "description": "spider tags",
            "required": False,
            "paramType": "form",
            "dataType": 'string'
        }, {
            "name": "desc",
            "description": "spider desc",
            "required": False,
            "paramType": "form",
            "dataType": 'string'
        }])
    def put(self, project_id, spider_id):
        spider_instance = SpiderInstance.query.filter_by(project_id=project_id, id=spider_id).first()
        if not spider_instance: abort(404)
        job_instance = JobInstance()
        job_instance.spider_name = spider_instance.spider_name
        job_instance.project_id = project_id
        job_instance.spider_arguments = request.form.get('spider_arguments')
        job_instance.desc = request.form.get('desc')
        job_instance.tags = request.form.get('tags')
        job_instance.run_type = JobRunType.ONETIME
        job_instance.priority = request.form.get('priority', 0)
        job_instance.enabled = -1
        db.session.add(job_instance)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e
        agent.start_spider(job_instance)
        return True


JOB_INSTANCE_FIELDS = [column.name for column in JobInstance.__table__.columns]
JOB_INSTANCE_FIELDS.remove('id')
JOB_INSTANCE_FIELDS.remove('date_created')
JOB_INSTANCE_FIELDS.remove('date_modified')


class JobCtrl(flask_restful.Resource):
    @swagger.operation(
        summary='list job instance',
        parameters=[{
            "name": "project_id",
            "description": "project id",
            "required": True,
            "paramType": "path",
            "dataType": 'int'
        }])
    def get(self, project_id):
        return [job_instance.to_dict() for job_instance in
                JobInstance.query.filter_by(run_type="periodic", project_id=project_id).all()]

    @swagger.operation(
        summary='add job instance',
        notes="json keys: <br>" + "<br>".join(JOB_INSTANCE_FIELDS),
        parameters=[{
            "name": "project_id",
            "description": "project id",
            "required": True,
            "paramType": "path",
            "dataType": 'int'
        }, {
            "name": "spider_name",
            "description": "spider_name",
            "required": True,
            "paramType": "form",
            "dataType": 'string'
        }, {
            "name": "spider_arguments",
            "description": "spider_arguments,  split by ','",
            "required": False,
            "paramType": "form",
            "dataType": 'string'
        }, {
            "name": "desc",
            "description": "desc",
            "required": False,
            "paramType": "form",
            "dataType": 'string'
        }, {
            "name": "tags",
            "description": "tags , split by ','",
            "required": False,
            "paramType": "form",
            "dataType": 'string'
        }, {
            "name": "run_type",
            "description": "onetime/periodic",
            "required": False,
            "paramType": "form",
            "dataType": 'string'
        }, {
            "name": "priority",
            "description": "LOW: -1, NORMAL: 0, HIGH: 1, HIGHEST: 2",
            "required": False,
            "paramType": "form",
            "dataType": 'int'
        }, {
            "name": "cron_minutes",
            "description": "@see http://apscheduler.readthedocs.io/en/latest/modules/triggers/cron.html",
            "required": False,
            "paramType": "form",
            "dataType": 'string'
        }, {
            "name": "cron_hour",
            "description": "",
            "required": False,
            "paramType": "form",
            "dataType": 'string'
        }, {
            "name": "cron_day_of_month",
            "description": "",
            "required": False,
            "paramType": "form",
            "dataType": 'string'
        }, {
            "name": "cron_day_of_week",
            "description": "",
            "required": False,
            "paramType": "form",
            "dataType": 'string'
        }, {
            "name": "cron_month",
            "description": "",
            "required": False,
            "paramType": "form",
            "dataType": 'string'
        }])
    def post(self, project_id):
        post_data = request.form
        if post_data:
            job_instance = JobInstance()
            job_instance.spider_name = post_data['spider_name']
            job_instance.project_id = project_id
            job_instance.spider_arguments = post_data.get('spider_arguments')
            job_instance.desc = post_data.get('desc')
            job_instance.tags = post_data.get('tags')
            job_instance.run_type = post_data['run_type']
            job_instance.priority = post_data.get('priority', 0)
            if job_instance.run_type == "periodic":
                job_instance.cron_minutes = post_data.get('cron_minutes') or '0'
                job_instance.cron_hour = post_data.get('cron_hour') or '*'
                job_instance.cron_day_of_month = post_data.get('cron_day_of_month') or '*'
                job_instance.cron_day_of_week = post_data.get('cron_day_of_week') or '*'
                job_instance.cron_month = post_data.get('cron_month') or '*'
            db.session.add(job_instance)
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                raise e
            return True


class JobDetailCtrl(flask_restful.Resource):
    @swagger.operation(
        summary='update job instance',
        notes="json keys: <br>" + "<br>".join(JOB_INSTANCE_FIELDS),
        parameters=[{
            "name": "project_id",
            "description": "project id",
            "required": True,
            "paramType": "path",
            "dataType": 'int'
        }, {
            "name": "job_id",
            "description": "job instance id",
            "required": True,
            "paramType": "path",
            "dataType": 'int'
        }, {
            "name": "spider_name",
            "description": "spider_name",
            "required": False,
            "paramType": "form",
            "dataType": 'string'
        }, {
            "name": "spider_arguments",
            "description": "spider_arguments,  split by ','",
            "required": False,
            "paramType": "form",
            "dataType": 'string'
        }, {
            "name": "desc",
            "description": "desc",
            "required": False,
            "paramType": "form",
            "dataType": 'string'
        }, {
            "name": "tags",
            "description": "tags , split by ','",
            "required": False,
            "paramType": "form",
            "dataType": 'string'
        }, {
            "name": "run_type",
            "description": "onetime/periodic",
            "required": False,
            "paramType": "form",
            "dataType": 'string'
        }, {
            "name": "priority",
            "description": "LOW: -1, NORMAL: 0, HIGH: 1, HIGHEST: 2",
            "required": False,
            "paramType": "form",
            "dataType": 'int'
        }, {
            "name": "cron_minutes",
            "description": "@see http://apscheduler.readthedocs.io/en/latest/modules/triggers/cron.html",
            "required": False,
            "paramType": "form",
            "dataType": 'string'
        }, {
            "name": "cron_hour",
            "description": "",
            "required": False,
            "paramType": "form",
            "dataType": 'string'
        }, {
            "name": "cron_day_of_month",
            "description": "",
            "required": False,
            "paramType": "form",
            "dataType": 'string'
        }, {
            "name": "cron_day_of_week",
            "description": "",
            "required": False,
            "paramType": "form",
            "dataType": 'string'
        }, {
            "name": "cron_month",
            "description": "",
            "required": False,
            "paramType": "form",
            "dataType": 'string'
        }, {
            "name": "enabled",
            "description": "-1 / 0, default: 0",
            "required": False,
            "paramType": "form",
            "dataType": 'int'
        }, {
            "name": "status",
            "description": "if set to 'run' will run the job",
            "required": False,
            "paramType": "form",
            "dataType": 'int'
        }

        ])
    def put(self, project_id, job_id):
        post_data = request.form
        if post_data:
            job_instance = JobInstance.query.filter_by(project_id=project_id, id=job_id).first()
            if not job_instance: abort(404)
            job_instance.spider_arguments = post_data.get('spider_arguments') or job_instance.spider_arguments
            job_instance.priority = post_data.get('priority') or job_instance.priority
            job_instance.enabled = post_data.get('enabled', 0)
            job_instance.cron_minutes = post_data.get('cron_minutes') or job_instance.cron_minutes
            job_instance.cron_hour = post_data.get('cron_hour') or job_instance.cron_hour
            job_instance.cron_day_of_month = post_data.get('cron_day_of_month') or job_instance.cron_day_of_month
            job_instance.cron_day_of_week = post_data.get('cron_day_of_week') or job_instance.cron_day_of_week
            job_instance.cron_month = post_data.get('cron_month') or job_instance.cron_month
            job_instance.desc = post_data.get('desc', 0) or job_instance.desc
            job_instance.tags = post_data.get('tags', 0) or job_instance.tags
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                raise e
            if post_data.get('status') == 'run':
                agent.start_spider(job_instance)
            return True


class JobExecutionCtrl(flask_restful.Resource):
    @swagger.operation(
        summary='list job execution status',
        parameters=[{
            "name": "project_id",
            "description": "project id",
            "required": True,
            "paramType": "path",
            "dataType": 'int'
        }])
    def get(self, project_id):
        return JobExecution.list_jobs(project_id)


class JobExecutionDetailCtrl(flask_restful.Resource):
    @swagger.operation(
        summary='stop job',
        notes='',
        parameters=[
            {
                "name": "project_id",
                "description": "project id",
                "required": True,
                "paramType": "path",
                "dataType": 'int'
            },
            {
                "name": "job_exec_id",
                "description": "job_execution_id",
                "required": True,
                "paramType": "path",
                "dataType": 'string'
            }
        ])
    def put(self, project_id, job_exec_id):
        job_execution = JobExecution.query.filter_by(project_id=project_id, id=job_exec_id).first()
        if job_execution:
            agent.cancel_spider(job_execution)
            return True


api.add_resource(ProjectCtrl, "/api/projects")
api.add_resource(SpiderCtrl, "/api/projects/<project_id>/spiders")
api.add_resource(SpiderDetailCtrl, "/api/projects/<project_id>/spiders/<spider_id>")
api.add_resource(JobCtrl, "/api/projects/<project_id>/jobs")
api.add_resource(JobDetailCtrl, "/api/projects/<project_id>/jobs/<job_id>")
api.add_resource(JobExecutionCtrl, "/api/projects/<project_id>/jobexecs")
api.add_resource(JobExecutionDetailCtrl, "/api/projects/<project_id>/jobexecs/<job_exec_id>")

'''
========= Router =========
'''


@app.before_request
def intercept_no_project():
    if request.path.find('/project//') > -1:
        flash("create project first")
        return redirect("/project/manage", code=302)


@app.context_processor
def inject_common():
    return dict(now=datetime.datetime.now(), servers=agent.servers)


@app.context_processor
def inject_project():
    project_context = {}
    project_context['project_list'] = Project.query.all()
    if project_context['project_list'] and (not session.get('project_id')):
        project = Project.query.first()
        session['project_id'] = project.id
    if session.get('project_id'):
        project_context['project'] = Project.find_project_by_id(session['project_id'])
        project_context['spider_list'] = [spider_instance.to_dict() for spider_instance in
                                          SpiderInstance.query.filter_by(project_id=session['project_id']).order_by(
                                              SpiderInstance.spider_name).all()]
    else:
        project_context['project'] = {}
    return project_context


@app.context_processor
def utility_processor():
    def timedelta(end_time, start_time):
        '''

        :param end_time:
        :param start_time:
        :param unit: s m h
        :return:
        '''
        if not end_time or not start_time:
            return ''
        if type(end_time) == str:
            end_time = datetime.datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
        if type(start_time) == str:
            start_time = datetime.datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
        total_seconds = (end_time - start_time).total_seconds()
        return readable_time(total_seconds)

    def readable_time(total_seconds):
        if not total_seconds:
            return '-'
        if total_seconds < 60:
            return '%s s' % total_seconds
        if total_seconds < 3600:
            return '%s m' % int(total_seconds / 60)
        return '%s h %s m' % (int(total_seconds / 3600), int((total_seconds % 3600) / 60))

    return dict(timedelta=timedelta, readable_time=readable_time)


@app.route("/")
def index():
    project = Project.query.first()
    if project:
        return redirect("/project/%s/job/dashboard" % project.id, code=302)
    return redirect("/project/manage", code=302)


@app.route("/project/<project_id>")
def project_index(project_id):
    session['project_id'] = project_id
    return redirect("/project/%s/job/dashboard" % project_id, code=302)


@app.route("/project/create", methods=['post'])
def project_create():
    project_name = request.form['project_name']
    project = Project()
    project.project_name = project_name
    db.session.add(project)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e
    return redirect("/project/%s/spider/deploy" % project.id, code=302)


@app.route("/project/<project_id>/delete")
def project_delete(project_id):
    project = Project.find_project_by_id(project_id)
    agent.delete_project(project)
    db.session.delete(project)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e
    return redirect("/project/manage", code=302)


@app.route("/project/manage")
def project_manage():
    return render_template("project_manage.html")


@app.route("/project/<project_id>/job/dashboard")
def job_dashboard(project_id):
    return render_template("job_dashboard.html", job_status=JobExecution.list_jobs(project_id), bit_enabled=config.BACK_IN_TIME_ENABLED)


@app.route("/project/<project_id>/job/favorites", methods=['GET', 'POST'])
def job_favorites(project_id):
    unique_spiders = set()
    unique_favorite_jobs = list()

    if request.method == 'POST':
        favorite_spiders = list(filter(None, request.form['favorite'].split(',')))
        jobs = JobExecution.favorite_spiders_jobs(project_id, favorite_spiders, 5000) if favorite_spiders else []

        #  keep only one instance for every spider
        for job in jobs:
            instance = job['job_instance']
            if instance.get('spider_name') not in unique_spiders:
                unique_favorite_jobs.append(job)
            unique_spiders.add(instance.get('spider_name'))

    return render_template("job_favorites.html", job_status=unique_favorite_jobs, method=request.method)


@app.route("/project/<project_id>/job/periodic")
def job_periodic(project_id):
    project = Project.find_project_by_id(project_id)
    job_instance_list = [job_instance.to_dict() for job_instance in
                         JobInstance.query.filter_by(run_type="periodic", project_id=project_id).order_by(
                             JobInstance.spider_name).all()]
    return render_template("job_periodic.html",
                           job_instance_list=job_instance_list)


@app.route("/project/<project_id>/job/add", methods=['post'])
def job_add(project_id):
    project = Project.find_project_by_id(project_id)
    job_instance = JobInstance()
    job_instance.spider_name = request.form['spider_name']
    job_instance.project_id = project_id
    job_instance.spider_arguments = request.form['spider_arguments']
    job_instance.priority = request.form.get('priority', 0)
    job_instance.run_type = request.form['run_type']
    # chose daemon manually
    if request.form['daemon'] != 'auto':
        spider_args = []
        if request.form['spider_arguments']:
            spider_args = request.form['spider_arguments'].split(",")
        spider_args.append("daemon={}".format(request.form['daemon']))
        job_instance.spider_arguments = ','.join(spider_args)
    if job_instance.run_type == JobRunType.ONETIME:
        job_instance.enabled = -1
        db.session.add(job_instance)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e
        agent.start_spider(job_instance)
    if job_instance.run_type == JobRunType.PERIODIC:
        job_instance.cron_minutes = request.form.get('cron_minutes') or '0'
        job_instance.cron_hour = request.form.get('cron_hour') or '*'
        job_instance.cron_day_of_month = request.form.get('cron_day_of_month') or '*'
        job_instance.cron_day_of_week = request.form.get('cron_day_of_week') or '*'
        job_instance.cron_month = request.form.get('cron_month') or '*'
        # set cron exp manually
        if request.form.get('cron_exp'):
            job_instance.cron_minutes, job_instance.cron_hour, job_instance.cron_day_of_month, job_instance.cron_month, job_instance.cron_day_of_week = \
                request.form['cron_exp'].split(' ')
        db.session.add(job_instance)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e
    return redirect(request.referrer, code=302)


@app.route("/project/<project_id>/job/addlist", methods=['post'])
def job_addlist(project_id):
    project = Project.find_project_by_id(project_id)
    spider_names = request.form.getlist('spider_name')
    for spider in spider_names:
        job_instance = JobInstance()
        job_instance.project_id = project_id
        job_instance.spider_name = spider
        job_instance.spider_arguments = request.form['spider_arguments']
        job_instance.priority = request.form.get('priority', 0)
        job_instance.run_type = request.form['run_type']
        job_instance.overlapping = bool(request.form.get('overlapping', False))
        # chose daemon manually
        if request.form['daemon'] != 'auto':
            spider_args = []
            if request.form['spider_arguments']:
                spider_args = request.form['spider_arguments'].split(",")
            spider_args.append("daemon={}".format(request.form['daemon']))
            job_instance.spider_arguments = ','.join(spider_args)
        if job_instance.run_type == JobRunType.ONETIME:
            job_instance.enabled = -1
            db.session.add(job_instance)
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                raise e
            agent.start_spider(job_instance)
        if job_instance.run_type == JobRunType.PERIODIC:
            job_instance.cron_minutes = request.form.get('cron_minutes') or '0'
            job_instance.cron_hour = request.form.get('cron_hour') or '*'
            job_instance.cron_day_of_month = request.form.get('cron_day_of_month') or '*'
            job_instance.cron_day_of_week = request.form.get('cron_day_of_week') or '*'
            job_instance.cron_month = request.form.get('cron_month') or '*'
            # set cron exp manually
            if request.form.get('cron_exp'):
                job_instance.cron_minutes, job_instance.cron_hour, job_instance.cron_day_of_month, job_instance.cron_month, job_instance.cron_day_of_week = \
                    request.form['cron_exp'].split(' ')
            db.session.add(job_instance)
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                raise e
    return redirect(request.referrer, code=302)


@app.route("/project/<project_id>/job/back-in-time", methods=['post'])
def job_back_in_time(project_id):
    if not config.BACK_IN_TIME_ENABLED:
        return redirect(request.referrer, code=302)

    spider_names = request.form.getlist('spider_name')
    for spider in spider_names:
        job_instance = JobInstance()
        job_instance.project_id = project_id
        job_instance.spider_name = spider

        spider_args = request.form['spider_arguments'].split(",")
        spider_args.append("--callback={}".format(request.form['callback']))
        spider_args.append("SCRAPY_PROJECT=SCRAPY_PROJECT")
        job_instance.spider_arguments = ','.join(spider_args)

        job_instance.priority = request.form.get('priority', 0)
        job_instance.run_type = JobRunType.ONETIME
        job_instance.overlapping = True
        # chose daemon manually
        if request.form['daemon'] != 'auto':
            spider_args = []
            if request.form['spider_arguments']:
                spider_args = request.form['spider_arguments'].split(",")
            spider_args.append("daemon={}".format(request.form['daemon']))
            job_instance.spider_arguments = ','.join(spider_args)

        job_instance.enabled = -1
        db.session.add(job_instance)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e
        agent.run_back_in_time(job_instance)
    return redirect(request.referrer, code=302)


@app.route("/project/<project_id>/jobexecs/<job_exec_id>/stop")
def job_stop(project_id, job_exec_id):
    job_execution = JobExecution.query.filter_by(project_id=project_id, id=job_exec_id).first()
    agent.cancel_spider(job_execution)
    return redirect(request.referrer, code=302)


@app.route("/project/<project_id>/jobexecs/<job_exec_id>/log")
def job_log(project_id, job_exec_id):
    job_execution = JobExecution.query.filter_by(project_id=project_id, id=job_exec_id).first()
    dim = requests.head(agent.log_url(job_execution)).headers._store.get('content-length', ['', '0'])[1]
    if int(dim) > 15728640:
        return redirect(agent.log_url(job_execution), code = 302)
    else:
        res = requests.get(agent.log_url(job_execution))
        res.encoding = 'utf8'
        raw = res.text
        return render_template("job_log.html", log_lines=raw.split('\n'))


@app.route("/project/<project_id>/jobexecs/<job_exec_id>/remove")
def job_exec_remove(project_id, job_exec_id):
    job_execution = JobExecution.query.filter_by(project_id=project_id, id=job_exec_id).first()
    db.session.delete(job_execution)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e
    return redirect(request.referrer, code=302)


@app.route("/project/<project_id>/job/<job_instance_id>/run")
def job_run(project_id, job_instance_id):
    job_instance = JobInstance.query.filter_by(project_id=project_id, id=job_instance_id).first()
    agent.start_spider(job_instance)
    return redirect(request.referrer, code=302)


@app.route("/project/<project_id>/job/<job_instance_id>/remove")
def job_remove(project_id, job_instance_id):
    job_instance = JobInstance.query.filter_by(project_id=project_id, id=job_instance_id).first()
    db.session.delete(job_instance)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e
    return redirect(request.referrer, code=302)


@app.route("/project/<project_id>/job/<job_instance_id>/switch")
def job_switch(project_id, job_instance_id):
    job_instance = JobInstance.query.filter_by(project_id=project_id, id=job_instance_id).first()
    job_instance.enabled = -1 if job_instance.enabled == 0 else 0
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e
    return redirect(request.referrer, code=302)


@app.route("/project/<project_id>/job/<job_instance_id>/switch-overlapping")
def job_switch_overlapping(project_id, job_instance_id):
    job_instance = JobInstance.query.filter_by(project_id=project_id, id=job_instance_id).first()
    job_instance.overlapping = True if not job_instance.overlapping else False
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e
    return redirect(request.referrer, code=302)


@app.route("/project/<project_id>/spider/dashboard")
def spider_dashboard(project_id):
    spider_instance_list = SpiderInstance.list_spiders(project_id)
    return render_template("spider_dashboard.html",
                           spider_instance_list=spider_instance_list, auto_scheduling_enabled=config.AUTO_SCHEDULE_ENABLED)


@app.route("/project/<project_id>/spider/deploy")
def spider_deploy(project_id):
    project = Project.find_project_by_id(project_id)
    return render_template("spider_deploy.html")


@app.route("/project/<project_id>/spider/upload", methods=['post'])
def spider_egg_upload(project_id):
    project = Project.find_project_by_id(project_id)
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.referrer)
    file = request.files['file']
    # if user does not select file, browser also
    # submit a empty part without filename
    if file.filename == '':
        flash('No selected file')
        return redirect(request.referrer)
    if file:
        filename = secure_filename(file.filename)
        dst = os.path.join(tempfile.gettempdir(), filename)
        file.save(dst)
        if agent.deploy(project, dst):
            flash('deploy success!')
        else:
            flash('deploy failed!')
    return redirect(request.referrer)

@app.route("/project/<project_id>/spider/<spider_id>/auto-schedule-switch")
def project_spider_auto_schedule(project_id, spider_id):
    spider_instance = SpiderInstance.query.filter_by(project_id=project_id, id=spider_id).first()
    spider_setup = SpiderSetup.get_spider_setup(spider_instance)
    spider_setup.auto_schedule = False if spider_setup.auto_schedule else True
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e

    return redirect(request.referrer, code=302)

@app.route("/project/<project_id>/<spider_id>/stats")
def project_stats(project_id, spider_id):
    if spider_id == "project":
        project = Project.find_project_by_id(project_id)
        spider = SpiderInstance.query.filter_by(project_id=project_id).all()

        for item in spider:
            item.spider_name = helper.prepare_spider_name(item.spider_name)

        working_time = JobExecution.list_working_time(project_id)
        last_run = JobExecution.list_last_run(project_id)
        quality_review = JobExecution.list_quality_review(project_id)
        last_ee = JobExecution.list_last_ee(project_id)
        run_stats = JobExecution.list_run_stats_by_hours(project_id)
        return render_template("project_stats.html", project=project, spider=spider, working_time=working_time,
                               last_run=last_run, quality_review=quality_review, last_ee=last_ee, run_stats=run_stats)

    elif spider_id == "server":
        project = Project.find_project_by_id(project_id)
        run_stats = JobExecution.list_run_stats_by_hours(project_id)
        request_stats = JobExecution.list_request_stats_by_hours(project_id, spider_id)
        item_stats = JobExecution.list_item_stats_by_hours(project_id, spider_id)
        return render_template("server_stats.html", run_stats=run_stats)

    else:
        project = Project.find_project_by_id(project_id)
        spider = SpiderInstance.query.filter_by(project_id=project_id, id=spider_id).first()
        results = JobExecution.list_spider_stats(project_id, spider_id)

        start_time = []
        end_time = []
        end_time_short = []
        duration_time = []
        requests_count = []
        items_count = []
        items_cached = []
        warnings_count = []
        errors_count = []
        bytes_count = []
        retries_count = []
        exceptions_count = []
        exceptions_size = []
        cache_size_count = []
        cache_object_count = []
        last_start_time = ""
        last_items_count = ""
        old_items_count = []
        items_dropped = []

        # Display date trick for small charts
        displayDates = False
        displayedDates = []
        for i in range(0, len(results)):
            if (results[i]['end_time'] != None) and (results[i]['end_time'].split(" ")[0] not in displayedDates):
                displayedDates.append(results[i]['end_time'].split(" ")[0])
        if len(displayedDates) > 2:
            displayDates = True

        # remove last JobInstance if not started or not finished
        if (len(results) > 0) and ((results[-1]['start_time'] == None) or (results[-1]['end_time'] == None)):
            results.pop()

        for i in range(0, len(results)):
            if i == len(results) - 1:
                last_start_time = results[i]['start_time']
                last_items_count = results[i]['items_count']
            else:
                old_items_count.append(results[i]['items_count'])

            start_time.append(results[i]['start_time'])
            end_time.append(results[i]['end_time'])
            duration_time.append((datetime.datetime.strptime(results[i]['end_time'],
                                                             '%Y-%m-%d %H:%M:%S') - datetime.datetime.strptime(
                results[i]['start_time'], '%Y-%m-%d %H:%M:%S')).total_seconds())

            if displayDates:
                end_time_short.append(end_time[-1].split(" ")[0])
            else:
                end_time_short.append(end_time[-1].split(" ")[1])

            requests_count.append(results[i]['requests_count'])
            items_dropped.append(results[i]['items_dropped'])
            items_count.append(results[i]['items_count'])
            if results[i]['items_count'] != 0:
                if results[i]['items_count'] - results[i]['requests_count'] >= 0:
                    items_cached.append(results[i]['items_count'] - results[i]['requests_count'])
                else:
                    items_cached.append(0)
            else:
                items_cached.append(0)
            warnings_count.append(results[i]['warnings_count'])
            errors_count.append(results[i]['errors_count'])
            bytes_count.append(results[i]['bytes_count'])
            retries_count.append(results[i]['retries_count'])

            exceptions_count.append(results[i]['exceptions_count'])
            if results[i]['exceptions_count'] > 10:
                exceptions_size.append(30)
            else:
                exceptions_size.append(results[i]['exceptions_count'] * 3)

            cache_size_count.append(results[i]['cache_size_count'])
            cache_object_count.append(results[i]['cache_object_count'])

        # tricks to have a nice gauge
        if len(results) == 0:
            min_items_count = 0
            max_items_count = 100
            average_items_count = 50
        else:
            (min_items_count, average_items_count, max_items_count) = _compute_item_stats(old_items_count,
                                                                                          last_items_count)

        last_runs = JobExecution.list_latest_jobs_for_spider(project.id, spider.spider_name)

        return render_template("spider_stats.html", spider=spider, start_time=start_time, end_time=end_time,
                               end_time_short=end_time_short, duration_time=duration_time,
                               last_start_time=last_start_time, last_items_count=last_items_count,
                               average_items_count=average_items_count,
                               min_items_count=min_items_count, max_items_count=max_items_count,
                               requests_count=requests_count, items_count=items_count, items_cached=items_cached,
                               warnings_count=warnings_count, errors_count=errors_count,
                               bytes_count=bytes_count, retries_count=retries_count, exceptions_count=exceptions_count,
                               exceptions_size=exceptions_size, last_runs=last_runs,
                               cache_size_count=cache_size_count, cache_object_count=cache_object_count,
                               items_dropped=items_dropped)


def _compute_item_stats(old_items_count, last_items_count):
    items_not_null = []
    for i in old_items_count:
        if i != 0:
            items_not_null.append(i)
    if len(items_not_null) == 0: items_not_null = [0]
    min_items_count = min(items_not_null)
    if len(old_items_count) == 0:
        max_items_count = last_items_count
    else:
        max_items_count = max(old_items_count)
    average_items_count = sum(items_not_null) / len(items_not_null)
    if max_items_count == 0:
        min_items_count = 0
    else:
        if (min_items_count / max_items_count) > 0.8:
            min_items_count = max_items_count * 0.8
        if (average_items_count / max_items_count) > 0.95 or max_items_count == last_items_count:
            max_items_count = average_items_count * 1.05

    return min_items_count, average_items_count, max_items_count