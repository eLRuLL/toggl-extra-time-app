import json
import random
import redis
import requests

from datetime import datetime, timedelta
from flask import Flask, request, render_template
from flask_sqlalchemy import SQLAlchemy

from flaskr.celery import make_celery


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/test.db'
app.config.update(
    CELERY_BROKER_URL='redis://localhost:6379',
    CELERY_RESULT_BACKEND='redis://localhost:6379',
)

db = SQLAlchemy(app)

celery = make_celery(app)


toggl_workspace = 3081165
# First user is the owner of the workspace, following users will be added to the respective projects
toggl_user_apikeys = ['915e1b6f71b4970efb0bb1f90cdcfa77', '5b3f5a766bf579df2a7f6895d70e9987']
toggl_user_ids = [4468826, 1749056]
toggl_pass = 'api_token'


start_date = datetime(2018, 9, 1)
date_period = timedelta(hours=1440)

redis_extra_time_key = 'toggl_extra_time'


class Toggl(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.Integer)
    client = db.Column(db.Integer)
    project = db.Column(db.Integer)
    time_entry = db.Column(db.Integer)
    time_entry_start_time = db.Column(db.DateTime)
    time_entry_duration = db.Column(db.Integer)
    time_entry_description = db.Column(db.String)


@app.route('/populate')
def populate():
    # create clients
    client_names = random.sample(range(1, 100), random.randint(2, 5))

    clients = []

    for client_name in client_names:
        client_info = requests.post(
            'https://www.toggl.com/api/v8/clients',
            headers={"Content-Type": "application/json"},
            data=json.dumps({"client": {"name": 'client{}'.format(client_name), "wid": toggl_workspace}}),
            auth=(toggl_user_apikeys[0], toggl_pass),
        )
        clients.append(client_info.json())

    # create projects
    project_names = random.sample(range(1, 100), 10)

    projects = []

    for project_name in project_names:
        project_info = requests.post(
            'https://www.toggl.com/api/v8/projects',
            data=json.dumps({
                "project": {
                    "name": "project{}".format(project_name),
                    "wid": toggl_workspace,
                    "is_private": True,
                    "cid": random.choice(clients)['data']['id'],
                },
            }),
            headers={"Content-Type": "application/json"},
            auth=(toggl_user_apikeys[0], toggl_pass),
        )
        projects.append(project_info.json())

    # adding user access to projects
    for x in toggl_user_ids[1:]:
        for project in projects:
            requests.post(
                'https://www.toggl.com/api/v8/project_users',
                data=json.dumps({
                    "project_user": {
                        "pid": project['data']['id'],
                        "uid": x,
                        "manager": True,
                    },
                }),
                headers={"Content-Type": "application/json"},
                auth=(toggl_user_apikeys[0], toggl_pass),
            )

    # create time entries for users
    time_entries = []

    for i in range(100):
        try:
            time_entry = requests.post(
                'https://www.toggl.com/api/v8/time_entries',
                data=json.dumps({
                    "time_entry": {
                        "description": "description{}".format(i),
                        "duration": random.randint(300, 28800),
                        "start": (start_date + timedelta(hours=random.randint(0, 1440))).isoformat() + '.000Z',
                        "pid": random.choice(projects)['data']['id'],
                        "created_with": "curl",
                    }
                }),
                headers={"Content-Type": "application/json"},
                auth=(random.choice(toggl_user_apikeys), toggl_pass),
            )
            time_entries.append(time_entry.json())
        except:
            print(f'{time_entry.status_code}: {time_entry.text}')

    return json.dumps({
        'workspace': toggl_workspace,
        'users': toggl_user_ids,
        'clients': clients,
        'projects': projects,
        'time_entries': time_entries,
    })


@app.route('/define', methods=['POST'])
def define_time_consuming_task():
    request_data = request.get_json()
    if request_data and 'time' in request_data:
        r = redis.Redis(host='localhost', port=6379)
        r.set(redis_extra_time_key, request_data['time'])
        return 'SUCCESS'
    else:
        return 'FAILURE'


@app.route('/table', defaults={'sort': None})
@app.route('/table/<sort>')
def info_table(sort):
    r = redis.Redis(host='localhost', port=6379)
    hours = int(r.get(redis_extra_time_key))
    if not sort:
        toggl_entries = Toggl.query.filter(Toggl.time_entry_duration >= hours*3600).all()
    else:
        if sort in ['client', 'project', 'time_entry_duration', 'time_entry_start_time']:
            toggl_entries = Toggl.query.filter(Toggl.time_entry_duration >= hours * 3600).order_by(
                getattr(Toggl, sort).desc()
            ).all()
        else:
            return "FAILURE"

    return render_template('time.html', entries=toggl_entries)


@celery.task()
def save_toggl_workspace():
    db.session.query(Toggl).delete()
    db.session.commit()

    # getting projects
    projects_response = requests.get(
        'https://www.toggl.com/api/v8/workspaces/{}/projects'.format(toggl_workspace),
        headers={"Content-Type": "application/json"},
        auth=(toggl_user_apikeys[0], toggl_pass),
    ).json()

    projects = {x['id']: x for x in projects_response}

    # getting time_entries
    for i, apikey in enumerate(toggl_user_apikeys):
        time_entries = requests.get(
            'https://www.toggl.com/api/v8/time_entries?start_date={start}&end_date={end}'.format(
                start=start_date.isoformat() + '.000Z',
                end=(start_date + date_period).isoformat() + '.000Z',
            ),
            headers={"Content-Type": "application/json"},
            auth=(apikey, toggl_pass),
        ).json()

        for time_entry in time_entries:
            if time_entry['wid'] == toggl_workspace:
                toggl_entry = Toggl(
                    user=toggl_user_ids[i],
                    project=time_entry['pid'],
                    time_entry=time_entry['id'],
                    client=projects[time_entry['pid']]['cid'],
                    time_entry_description=time_entry['description'],
                    time_entry_start_time=datetime.strptime(time_entry['start'], '%Y-%m-%dT%H:%M:%S+00:00'),
                    time_entry_duration=time_entry['duration'],
                )
                db.session.add(toggl_entry)
        db.session.commit()


