#!/bin/bash

set -eu

_root_dir=$(dirname $(dirname $(readlink -f $0)))
cd ${_root_dir}/devutils
python3 -m pytest -c ${_root_dir}/devutils/pytest.ini
