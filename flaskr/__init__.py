import json
import random
import requests

from datetime import datetime, timedelta
from flask import Flask
from flask_sqlalchemy import SQLAlchemy


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/test.db'
db = SQLAlchemy(app)

toggl_workspace = 3079970

# First user is the owner of the workspace, following users will be added to the respective projects
toggl_user_apikeys = ['915e1b6f71b4970efb0bb1f90cdcfa77', '5b3f5a766bf579df2a7f6895d70e9987']
toggl_user_ids = [4468826, 1749056]
toggl_pass = 'api_token'


class Toggl(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.Integer)
    client = db.Column(db.Integer)
    project = db.Column(db.Integer)
    time_entry = db.Column(db.Integer)


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
        time_entry = requests.post(
            'https://www.toggl.com/api/v8/time_entries',
            data=json.dumps({
                "time_entry": {
                    "description": "description{}".format(i),
                    "duration": random.randint(300, 28800),
                    "start": (datetime(2018, 9, 1) + timedelta(hours=random.randint(0, 1440))).isoformat() + '.000Z',
                    "pid": random.choice(projects)['data']['id'],
                    "created_with": "curl",
                }
            }),
            headers={"Content-Type": "application/json"},
            auth=(random.choice(toggl_user_apikeys), toggl_pass),
        )
        time_entries.append(time_entry.json())

    return json.dumps({
        'workspace': toggl_workspace,
        'users': toggl_user_ids,
        'clients': clients,
        'projects': projects,
        'time_entries': time_entries,
    })
