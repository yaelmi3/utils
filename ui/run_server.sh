#!/usr/bin/env bash

source env/bin/activate
export LOGS_DIR=/var/log/gunicorn
export PYTHONPATH=$PWD
gunicorn ui.webui:app -k gevent --log-file=${LOGS_DIR}/webui_gunicorn.log \
--access-logfile=${LOGS_DIR}/webui_access_gunicron.log\
 --error-logfile=${LOGS_DIR}/webui_gunicorn_errors.log\
  --workers 10 --max-requests 50000 --bind=0.0.0.0:8080 --timeout 3600\
   --capture-output --enable-stdio-inheritance -D