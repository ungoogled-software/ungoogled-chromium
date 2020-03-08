#!/bin/bash

# Wrapper for devutils and utils formatter, linter, and tester

set -eu

_root_dir=$(dirname $(dirname $(readlink -f $0)))
cd ${_root_dir}/devutils

printf '###### utils yapf ######\n'
./run_utils_yapf.sh
printf '###### utils pylint ######\n'
./run_utils_pylint.py || ./run_utils_pylint.py --hide-fixme
printf '###### utils tests ######\n'
./run_utils_tests.sh

printf '### devutils yapf ######\n'
./run_devutils_yapf.sh
printf '###### devutils pylint ######\n'
./run_devutils_pylint.py || ./run_devutils_pylint.py --hide-fixme
printf '###### devutils tests ######\n'
./run_devutils_tests.sh
