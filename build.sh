#!/bin/bash

BUILD_SANDBOX_PATH=$(dirname $0)/build-sandbox

pushd $BUILD_SANDBOX_PATH

rm -r debian
cp $(dirname $0)/debian ./

./debian/rules download-source
dpkg-buildpackage -b -uc

popd $BUILD_SANDBOX_PATH
