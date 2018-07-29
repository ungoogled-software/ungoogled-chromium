#!/bin/bash

set -eux

python3 -m yapf --style '.style.yapf' -e '*/third_party/*' -rpi buildkit
