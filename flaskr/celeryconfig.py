from celery.schedules import crontab


CELERY_IMPORTS = 'flaskr'
CELERY_TASK_RESULT_EXPIRES = 30
CELERY_TIMEZONE = 'UTC'

CELERY_ACCEPT_CONTENT = ['json', 'msgpack', 'yaml']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'

CELERYBEAT_SCHEDULE = {
    'my-task-test': {
        'task': 'flaskr.save_toggl_workspace',
        # Every minute
        'schedule': crontab(minute="*"),
    }
}