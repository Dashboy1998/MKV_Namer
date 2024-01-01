#!/bin/bash

source enviroment_vars.conf
python -m venv "$python_venv"

python ./MKV_Namer.py
