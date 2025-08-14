#!/bin/bash

if [[ ! -f "venv/bin/activate" ]]; then
    python3 -m venv venv &>/dev/null
fi

source "venv/bin/activate"
eval "pip3 install --upgrade -r requirements.txt"