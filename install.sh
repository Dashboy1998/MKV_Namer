#!/bin/bash

python_venv="./MakeMKV_Namer"

python -m venv "$python_venv"

source "$python_venv"
pip install -r ./requirements
