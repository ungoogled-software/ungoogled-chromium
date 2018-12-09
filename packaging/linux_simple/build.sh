#!/bin/bash

set -eux

# Simple build script for Linux

BUNDLE=linux_portable

# Place download_cache next the source tree, which is usually build/src
DOWNLOAD_CACHE=$(dirname $(readlink -f $0))/../../download_cache

rm -rf out || true
mkdir out
mkdir out/Default

pushd $(dirname $(readlink -f $0))
mkdir $DOWNLOAD_CACHE || true
python3 -m buildkit downloads retrieve -b config_bundles/$BUNDLE -c $DOWNLOAD_CACHE
python3 -m buildkit downloads unpack -b config_bundles/$BUNDLE -c $DOWNLOAD_CACHE ../
python3 -m buildkit prune -b config_bundles/$BUNDLE ../
python3 -m buildkit patches apply -b config_bundles/$BUNDLE ../
python3 -m buildkit domains apply -b config_bundles/$BUNDLE -c domainsubcache.tar.gz ../
python3 -m buildkit gnargs print -b config_bundles/$BUNDLE > ../out/Default/args.gn
popd

# Set commands or paths to LLVM-provided tools outside the script via 'export ...'
# or before these lines
export AR=${AR:=llvm-ar}
export NM=${NM:=llvm-nm}
export CC=${CC:=clang}
export CXX=${CXX:=clang++}
# You may also set CFLAGS, CPPFLAGS, CXXFLAGS, and LDFLAGS
# See build/toolchain/linux/unbundle/ in the Chromium source for more details.

./tools/gn/bootstrap/bootstrap.py -o out/Default/gn --skip-generate-buildfiles
./out/Default/gn gen out/Default --fail-on-unused-args
ninja -C out/Default chrome chrome_sandbox chromedriver
