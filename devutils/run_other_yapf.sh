#!/bin/bash

set -eu

python3 -m yapf --style "$(dirname $(readlink -f $0))/.style.yapf" -rpi $@
