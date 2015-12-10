#!/bin/bash

SCRIPT_DIR=$(dirname $(readlink -f $0))
BUILD_SANDBOX_PATH=$SCRIPT_DIR/build-sandbox
OLD_DIR=$(pwd)

mkdir $BUILD_SANDBOX_PATH

cd $BUILD_SANDBOX_PATH

rm -r debian
cp -ri $SCRIPT_DIR/build_templates/debian ./
cp -ri $SCRIPT_DIR/patches/. ./debian/patches
cat ./debian/patches/series >> ./debian/patches/patch_order
rm ./debian/patches/series
mv ./debian/patches/patch_order ./debian/patches/series

cd $OLD_DIR

echo "Done. Debian build scripts in $BUILD_SANDBOX_PATH"
