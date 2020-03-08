#!/bin/bash

set -eu

_current_dir=$(dirname $(readlink -f $0))
_root_dir=$(dirname $_current_dir)
python3 -m yapf --style "$_root_dir/.style.yapf" -e '*/third_party/*' -rpi "$_current_dir"
