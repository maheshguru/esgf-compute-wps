#! /bin/bash

app_root="/var/www/compute/compute"

python $app_root/manage.py collectstatic --no-input

python $app_root/manage.py migrate

gunicorn -b 0.0.0.0:8000 --reload --chdir $app_root/ compute.wsgi $@
