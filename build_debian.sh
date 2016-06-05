#!/bin/bash

# Script to build Debian packages

set -e -u

SCRIPT_DIR=$(dirname $(readlink -f $0));
CWD=$(pwd);

SANDBOX_PATH="$SCRIPT_DIR/build-sandbox";
DOWNLOAD_EXTRACT_TARBALL=;
CUSTOM_TARBALL=;
REMOVE_TARBALL=;
EVALUATE_CLEANING_LIST=;
GENERATE_BUILD_SCRIPTS=;
RUN_BUILD_COMMAND=;

print_usage() {
    echo "Usage: $0 [-h] {-A | [-d | -x tarball] [-R] [-c] [-g] [-b]}";
    echo "Options:";
    echo "  -h: Show this help message";
    echo "  -s: (Default: $SANDBOX_PATH) Path to to the building sandbox";
    echo "  -A: Same as -d -c -g -b";
    echo "  -d: Download the source tarball and extract it into the building sandbox. Cannot be used with -x";
    echo "  -x: Extract the provided tarball into the building sandbox. Cannot be used with -d";
    echo "  -R: Remove the tarball after source extraction. Otherwise it will be kept. Requires -d or -x to be present";
    echo "  -c: Delete the files defined in cleaning_list";
    echo "  -g: Generate Debian or Ubuntu build scripts (depending on lsb_release) and place them into the building sandbox, if they do not already exist";
    echo "  -b: Run dpkg-buildpackage";
}

is_not_set() {
    if [[ -n "$1" ]]; then
        eval "local to_check=\$$1;"
        if [[ -n "$to_check" ]]; then
            MESSAGE="Variable $1 is already set";
            if [[ -n "$2" ]]; then
                MESSAGE=$2;
            fi
            echo $MESSAGE >&2;
            exit 1;
        fi
    else
        echo "is_not_set() did not get an argument" >&2;
        exit 1;
    fi
}

set_if_empty() {
    if [[ -n "$1" ]] && [[ -n "$2" ]]; then
        eval "local to_check=\$$1;"
        if [[ -z "$to_check" ]]; then
            eval "$1=$2";
        fi
    else
        echo "set_if_empty() did not get two arguments" >&2;
        exit 1;
    fi
}

set_or_fail() {
    if [[ -n "$1" ]] && [[ -n "$2" ]] && [[ -n "$3" ]]; then
        is_not_set $1 "$3";
        set_if_empty $1 "$2";
    else
        echo "set_or_fail() did not get three arguments" >&2;
        exit 1;
    fi
}

while getopts ":hs:Adx:kcpgb" opt; do
    case $opt in
        h)
            print_usage;
            exit 0;
            ;;
        s)
            SANDBOX_PATH=$OPTARG;
            ;;
        A)
            A_conflict="Argument -A cannot be used with any other argument except -s";
            set_or_fail "DOWNLOAD_EXTRACT_TARBALL" 1 "$A_conflict";
            set_or_fail "REMOVE_TARBALL" 0 "$A_conflict";
            set_or_fail "EVALUATE_CLEANING_LIST" 1 "$A_conflict";
            set_or_fail "GENERATE_BUILD_SCRIPTS" 1 "$A_conflict";
            set_or_fail "RUN_BUILD_COMMAND" 1 "$A_conflict";
            unset A_conflict;
            ;;
        d)
            is_not_set "CUSTOM_TARBALL" "Argument -d cannot be used with -x";
            DOWNLOAD_EXTRACT_TARBALL=1;
            ;;
        x)
            is_not_set "DOWNLOAD_EXTRACT_TARBALL" "Argument -x cannot be used with -d";
            CUSTOM_TARBALL=$OPTARG;
            ;;
        R)
            REMOVE_TARBALL=1;
            ;;
        c)
            EVALUATE_CLEANING_LIST=1;
            ;;
        g)
            GENERATE_BUILD_SCRIPTS=1;
            ;;
        b)
            RUN_BUILD_COMMAND=1;
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

set_if_empty "DOWNLOAD_EXTRACT_TARBALL" 0
set_if_empty "REMOVE_TARBALL" 0
set_if_empty "EVALUATE_CLEANING_LIST" 0
set_if_empty "GENERATE_BUILD_SCRIPTS" 0
set_if_empty "RUN_BUILD_COMMAND" 0

if [[ $DOWNLOAD_EXTRACT_TARBALL -eq 1 ]]; then
    if [[ -e $SANDBOX_PATH ]]; then
        echo "Build sandbox path $SANDBOX_PATH already exists" >&2;
        exit 1;
    else
        mkdir $SANDBOX_PATH;
    fi
    echo "Downloading and extracting tarball...";
    if [[ $REMOVE_TARBALL -eq 1 ]]; then
        $SCRIPT_DIR/download_source.sh -x "$SANDBOX_PATH" -R
    else
        $SCRIPT_DIR/download_source.sh -x "$SANDBOX_PATH"
    fi
fi

if [[ -n "$CUSTOM_TARBALL" ]]; then
    if [[ -e $SANDBOX_PATH ]]; then
        echo "Build sandbox path $SANDBOX_PATH already exists" >&2;
        exit 1;
    else
        mkdir $SANDBOX_PATH;
    fi
    if [[ -f "$CUSTOM_TARBALL" ]]; then
        CUSTOM_TARBALL=$(readlink -f "$CUSTOM_TARBALL");
    else
        echo "Custom tarball $CUSTOM_TARBALL is not a file";
        exit 1;
    fi
    echo "Unpacking tarball $CUSTOM_TARBALL ...";
    cd "$SANDBOX_PATH";
    tar -xf "$CUSTOM_TARBALL" --strip-components=1;
    cd "$CWD";
    if [[ $REMOVE_TARBALL -eq 1 ]]; then
        rm $CUSTOM_TARBALL;
    fi
fi

if [[ ! -d $SANDBOX_PATH ]]; then
    echo "$SANDBOX_PATH is not a directory" >&2;
    exit 1;
fi

cd "$SANDBOX_PATH";

if [[ $EVALUATE_CLEANING_LIST -eq 1 ]]; then
    echo "Evaluating cleaning list..."
    $SCRIPT_DIR/evaluate_cleaning_list.py $SCRIPT_DIR/cleaning_list
fi

if [[ $GENERATE_BUILD_SCRIPTS -eq 1 ]]; then
    DISTRIBUTION=$(lsb_release -si);
    if [[ -e "$SANDBOX_PATH/debian" ]]; then
        echo "$DISTRIBUTION build scripts already exist. Skipping...";
    else
        echo "Generating $DISTRIBUTION build scripts...";
        if [[ "$DISTRIBUTION" == "Debian" ]]; then
            $SCRIPT_DIR/generate_debian_scripts.sh $SANDBOX_PATH;
        elif [[ "$DISTRIBUTION" == "Ubuntu" ]]; then
            $SCRIPT_DIR/generate_ubuntu_scripts.sh $SANDBOX_PATH;
        else
            echo "Invalid distribution name: $DISTRIBUTION" >&2;
            cd "$CWD"
            exit 1;
        fi
    fi
fi

if [[ $RUN_BUILD_COMMAND -eq 1 ]]; then
    echo "Running build command...";
    dpkg-buildpackage -b -uc
fi

cd "$CWD";

echo "Done";

