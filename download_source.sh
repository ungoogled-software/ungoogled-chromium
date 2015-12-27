#!/bin/bash

# A script that downloads the source tarball

CURRENT_DIR=$(dirname $(readlink -f $0));

DOWNLOAD_VERSION=;
DEBIAN_CHANGELOG=;
TARBALL_DESTINATION=$CURRENT_DIR;
EXTRACT_DESTINATION=;
REMOVE_AFTER_EXTRACTION=0;

print_usage() {
    echo "Usage: $0 [-h] [-v version | -c debian_changelog] [-d tarball_directory] [-x extract_directory | -x extract_directory -R]";
    echo "Options:";
    echo "  -h: Show this help message";
    echo "  -v: (No default) Specify the specific Chromium version to download";
    echo "  -c: (Default: $CURRENT_DIR/build_templates/debian/changelog) Path to a Debian changelog file";
    echo "  -d: (Default: $CURRENT_DIR) Directory to store the sourcecode tarball";
    echo "  -x: (Not enabled by default) Directory to extract the source tarball";
    echo "  -R: Remove the tarball after source extraction. Requires -x to be present";
}

while getopts ":v:c:d:x:Rh" opt; do
    case $opt in
        v)
            DOWNLOAD_VERSION=$OPTARG;
            ;;
        c)
            DEBIAN_CHANGELOG=$OPTARG;
            ;;
        d)
            TARBALL_DESTINATION=$OPTARG;
            ;;
        x)
            EXTRACT_DESTINATION=$OPTARG;
            ;;
        R)
            REMOVE_AFTER_EXTRACTION=1;
            ;;
        h)
            print_usage;
            exit 0;
            ;;
        \?)
            echo "Invalid option: -$OPTARG" >&2;
            print_usage;
            exit 1;
            ;;
        :)
            echo "Option -$OPTARG requires an argument." >&2;
            print_usage;
            exit 1;
            ;;
    esac
done

if [[ -n "$DOWNLOAD_VERSION" ]] && [[ -n "$DEBIAN_CHANGELOG" ]]; then
    echo "Arguments -v and -c cannot be used together" >&2;
    exit 1;
elif [[ -z "$EXTRACT_DESTINATION" ]] && [[ "$REMOVE_AFTER_EXTRACTION" == "1" ]]; then
    echo "Argument -R requires -x to be present" >&2;
    exit 1;
fi

if [[ -z "$DOWNLOAD_VERSION" ]] && [[ -z "$DEBIAN_CHANGELOG" ]]; then
    DEBIAN_CHANGELOG="$CURRENT_DIR/build_templates/debian/changelog";
fi

if [[ -n "$DEBIAN_CHANGELOG" ]]; then
    if [[ ! -f "$DEBIAN_CHANGELOG" ]]; then
        echo "Debian changelog at $DEBIAN_CHANGELOG is not a regular file" >&2;
        exit 1;
    fi
    echo "Reading version from $DEBIAN_CHANGELOG";
    DOWNLOAD_VERSION=$(dpkg-parsechangelog -l $DEBIAN_CHANGELOG -S Version | sed s/-.*//);
    if [[ -z "$DOWNLOAD_VERSION" ]]; then
        echo "Could not read the Debian changelog!" >&2;
        exit 1;
    fi
fi

if [[ ! -d "$TARBALL_DESTINATION" ]]; then
    echo "Tarball destination $TARBALL_DESTINATION is not a directory" >&2;
    exit 1;
fi

TARBALL="chromium-$DOWNLOAD_VERSION.tar.xz";
URL="https://gsdview.appspot.com/chromium-browser-official/$TARBALL";

echo "Downloading version $DOWNLOAD_VERSION to $TARBALL_DESTINATION ...";

wget -c -P $TARBALL_DESTINATION $URL;
if [[ $? -ne 0 ]]; then
    echo "Dowloading of source tarball failed!" >&2;
    exit 1;
fi

if [[ -n "$EXTRACT_DESTINATION" ]]; then
    echo "Extracting $TARBALL to $EXTRACTION_DESTINATION ...";
    if [[ ! -d "$EXTRACT_DESTINATION" ]]; then
        echo "Extraction destination $EXTRACT_DESTINATION is not a directory" >&2;
        exit 1;
    fi
    CWD=$(pwd);
    cd "$EXTRACTION_DESTINATION";
    tar -xf "$TARBALL_DESTINATION/$TARBALL" --strip-components=1;
    cd "$CWD";
    if [[ "$REMOVE_AFTER_EXTRACTION" == "1" ]]; then
        echo "Removing $TARBALL ...";
        rm $TARBALL
        if [[ $? -ne 0 ]]; then
            echo "Could not remove source tarball" >&2;
            exit 1;
        fi
    fi
fi
