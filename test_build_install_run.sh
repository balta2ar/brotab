#!/bin/bash

# How to use:
# rm -rf ./dist && python setup.py sdist bdist_wheel && docker build -t brotab-buildinstallrun . && docker run -it brotab-buildinstallrun

# Fail on any error
set -e

pip install $(find . -name *.whl -type f)

python -c 'from brotab.tests.test_main import run_mocked_mediators as run; run(count=3, default_port_offset=0, delay=0)' &
sleep 3

function run() {
    echo "Running: $*"
    $*
}

run bt list
run bt windows
run bt clients
run bt active
run bt words
run bt text

