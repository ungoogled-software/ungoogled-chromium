#!/bin/bash

set -eu

_root_dir=$(dirname $(dirname $(readlink -f $0)))
python3 -m yapf --style "$_root_dir/.style.yapf" -e '*/third_party/*' -rpi "$_root_dir/utils"
