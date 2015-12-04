#!/bin/bash

SCRIPT_DIR=$(dirname $(readlink -f $0))
BUILD_SANDBOX_PATH=$SCRIPT_DIR/build-sandbox
OLD_DIR=$(pwd)

mkdir $BUILD_SANDBOX_PATH

cd $BUILD_SANDBOX_PATH

rm -r debian
cp -r $SCRIPT_DIR/debian ./

./debian/rules download-source
dpkg-buildpackage -b -uc

cd $OLD_DIR
