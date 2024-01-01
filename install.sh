#!/bin/bash

set -e

source ./enviroment_vars.conf

python -m venv "$python_venv"

source "$python_venv/bin/activate"
pip install -r ./requirements.txt
