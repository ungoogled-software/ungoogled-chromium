#!/usr/bin/env bash

PACKAGING_DIR=$(dirname $(readlink -f $0))

cp -r $PACKAGING_DIR/SOURCES/* ~/rpm/SOURCES/

pushd $PACKAGING_DIR/chromium-icons_contents
tar cjf ~/rpm/SOURCES/chromium-icons.tar.bz2 *
popd

cp $PACKAGING_DIR/patches/*/*.patch ~/rpm/SOURCES
cp $PACKAGING_DIR/patches/*/*/*.patch ~/rpm/SOURCES
cp $PACKAGING_DIR/ungoogled-chromium.spec ~/rpm/SPECS/

mv $PACKAGING_DIR/../../tree ~/rpm/BUILD/tree
