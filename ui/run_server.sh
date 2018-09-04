#!/usr/bin/env bash

export PYTHONPATH=$PWD
gunicorn ui.webui:app -p webui.pid -b 0.0.0.0:8000 --workers=10 -D