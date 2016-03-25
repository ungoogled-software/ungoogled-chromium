#!/bin/bash

# Script to generate Ubuntu build scripts

set -e -u

if [[ -z "$1" ]]; then
    echo "Usage: $0 sandbox_directory" >&2;
    exit 1;
fi

SCRIPT_DIR=$(dirname $(readlink -f $0));
BUILD_SANDBOX=$1;

if [[ ! -d "$BUILD_SANDBOX" ]]; then
    echo "Path $BUILD_SANDBOX is not a directory" >&2;
    exit 1;
fi

CWD=$(pwd);
cd "$BUILD_SANDBOX";

if [[ -e "debian" ]]; then
    echo "Path $BUILD_SANDBOX/debian already exists" >&2;
    cd "$CWD";
    exit 1;
fi
cp -ri $SCRIPT_DIR/build_templates/debian ./
cp -r $SCRIPT_DIR/build_templates/ubuntu/* ./debian
cp -ri $SCRIPT_DIR/patches/. ./debian/patches
cat ./debian/patches/patch_order >> ./debian/patches/ubuntu_patches/ubuntu_patch_order
rm ./debian/patches/patch_order
cat ./debian/patches/series >> ./debian/patches/ubuntu_patches/ubuntu_patch_order
rm ./debian/patches/series
mv ./debian/patches/ubuntu_patches/ubuntu_patch_order ./debian/patches/series

cd "$CWD";
