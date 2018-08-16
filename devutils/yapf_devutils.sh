#!/bin/bash

set -eux

python3 -m yapf --style '.style.yapf' -rpi $@
