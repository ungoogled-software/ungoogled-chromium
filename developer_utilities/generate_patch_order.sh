#!/bin/bash

# Simple script to generate the patch order for a given configuration
# Takes two arguments: The config type, followed by the build directory
# (Specify different configurations to get differerent patch orders)
# Used in conjunction with set_quilt_vars.sh

set -e -u -x

patches_type=$1
ungoogled_chromium_dir="$(dirname $(dirname $(readlink -f $0)))"
build_dir=$2
assembled_resources=/tmp/tmp_ungoogled_assembled_resources

rm -r "$assembled_resources" || true
mkdir "$assembled_resources"
python3 "$ungoogled_chromium_dir/utilikit/export_resources.py" "$assembled_resources" "$patches_type"
cp -i "$assembled_resources/patch_order" "$build_dir/updating_patch_order"

