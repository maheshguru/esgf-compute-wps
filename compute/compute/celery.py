#! /usr/bin/env python

from __future__ import absolute_import
from __future__ import unicode_literals

import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'compute.settings')

app = Celery('compute',
        backend = os.getenv('CELERY_BACKEND', 'redis://0.0.0.0'),
        broker = os.getenv('CELERY_BROKER', 'redis://0.0.0.0'),
        )

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()

app.autodiscover_tasks(['wps.processes'])

@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))
