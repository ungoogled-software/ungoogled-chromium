#!/bin/bash

# Simple script to assemble patches into the sandbox for updating with quilt
# Takes one argument: Specify the configuration type to assemble patches for
# (Should be run multiple times with different configurations to update all of the patches)
# Used in conjunction with set_quilt_vars.sh

set -e -u -x

patches_type=$1
ungoogled_chromium_dir="$(dirname $(dirname $(readlink -f $0)))"
build_sandbox="$ungoogled_chromium_dir/build/sandbox"
patches_dir="$build_sandbox/ungoogled_patches"
assembled_resources=/tmp/tmp_assembled_resources

rm -r "$assembled_resources" || true
rm -r "$patches_dir" || true
export PYTHONPATH="$ungoogled_chromium_dir"
mkdir "$assembled_resources"
python3 -m utilities.assemble_resources "$patches_type" --output-dir "$assembled_resources"
#find "$assembled_resources/patches" -name "*.patch" | python3 -m utilities.substitute_domains --domain-regex-list "$assembled_resources/domain_regex_list" --root-dir "$assembled_resources/patches"
mkdir "$patches_dir"
cp -ri "$assembled_resources/patches" "$patches_dir"
cp -i "$assembled_resources/patch_order" "$patches_dir"

