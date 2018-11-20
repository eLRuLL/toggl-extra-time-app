# REQUIREMENTS

- [redis installation](https://redis.io/topics/quickstart)
- A Toggl workspace created by the main user and another used invited to
the same workspace


# CELERY

We need celery to make our routinary tasks, as saving toggl data to our
database:

To enable worker just run:

    celery worker -A flaskr.celery --loglevel=DEBUG

To enable the celery beat:

    celery beat -A flaskr.celery --schedule=/tmp/celerybeat-schedule --pidfile=/tmp/celerybeat.pid --loglevel=DEBUG


# APPLICATION

to run our application start it with:

    export FLASK_APP=flaskr
    flask run
