#!/bin/bash

# Script to build Debian packages

SCRIPT_DIR=$(dirname $(readlink -f $0));
CWD=$(pwd);

SANDBOX_PATH="$SCRIPT_DIR/build-sandbox";
DOWNLOAD_EXTRACT_TARBALL=;
CUSTOM_TARBALL=;
KEEP_TARBALL=;
RUN_SOURCE_CLEANER=;
RUN_DOMAIN_PATCHER=;
GENERATE_BUILD_SCRIPTS=;
RUN_BUILD_COMMAND=;

print_usage() {
    echo "Usage: $0 [-h] {-A | [-d | -x tarball] [-k] [-c] [-p] [-g] [-b]}";
    echo "Options:";
    echo "  -h: Show this help message";
    echo "  -s: (Default: $SANDBOX_PATH) Path to to the building sandbox";
    echo "  -A: Same as -d -c -p -g -b";
    echo "  -d: Download the source tarball and extract it into the building sandbox. Cannot be used with -x";
    echo "  -x: Extract the provided tarball into the building sandbox. Cannot be used with -d";
    echo "  -k: Keep the tarball after source extraction. Otherwise it will be deleted. Requires -d or -x to be present";
    echo "  -c: Run source_cleaner.sh on the source code";
    echo "  -p: Run domain_patcher.sh on the source code";
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

check_exit_status() {
    local exit_code=$?;
    local exit_message="(No message)";
    if [[ -n $1 ]]; then
        exit_message=$1;
    fi
    if [[ $exit_code -ne 0 ]]; then
        echo "Exit status $exit_code: $exit_message";
        cd "$CWD";
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
            set_or_fail "KEEP_TARBALL" 0 "$A_conflict";
            set_or_fail "RUN_SOURCE_CLEANER" 1 "$A_conflict";
            set_or_fail "RUN_DOMAIN_PATCHER" 1 "$A_conflict";
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
        k)
            KEEP_TARBALL=1;
            ;;
        c)
            RUN_SOURCE_CLEANER=1;
            ;;
        p)
            RUN_DOMAIN_PATCHER=1;
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
set_if_empty "KEEP_TARBALL" 0
set_if_empty "RUN_SOURCE_CLEANER" 0
set_if_empty "RUN_DOMAIN_PATCHER" 0
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
    if [[ $KEEP_TARBALL -eq 1 ]]; then
        $SCRIPT_DIR/download_source.sh -x "$SANDBOX_PATH"
        check_exit_status "Source downloading failed";
    else
        $SCRIPT_DIR/download_source.sh -x "$SANDBOX_PATH" -R
        check_exit_status "Source downloading failed";
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
    check_exit_status "Tarball extraction failed";
    cd "$CWD";
    if [[ $KEEP_TARBALL -eq 0 ]]; then
        rm $CUSTOM_TARBALL;
        check_exit_status "Could not remove custom tarball";
    fi
fi

if [[ ! -d $SANDBOX_PATH ]]; then
    echo "$SANDBOX_PATH is not a directory" >&2;
    exit 1;
fi

cd "$SANDBOX_PATH";

if [[ $RUN_SOURCE_CLEANER -eq 1 ]]; then
    echo "Running source cleaner...";
    $SCRIPT_DIR/source_cleaner.sh
    check_exit_status "Source cleaning encountered an error";
fi

if [[ $RUN_DOMAIN_PATCHER -eq 1 ]]; then
    echo "Running domain patcher...";
    $SCRIPT_DIR/domain_patcher.sh
    check_exit_status "Domain patching encountered an error";
fi;

if [[ $GENERATE_BUILD_SCRIPTS -eq 1 ]]; then
    DISTRIBUTION=$(lsb_release -si);
    if [[ -e "$SANDBOX_PATH/debian" ]]; then
        echo "$DISTRIBUTION build scripts already exist. Skipping...";
    else
        echo "Generating $DISTRIBUTION build scripts...";
        if [[ "$DISTRIBUTION" == "Debian" ]]; then
            $SCRIPT_DIR/generate_debian_scripts.sh $SANDBOX_PATH;
            check_exit_status "Could not generate $DISTRIBUTION build scripts";
        elif [[ "$DISTRIBUTION" == "Ubuntu" ]]; then
            $SCRIPT_DIR/generate_ubuntu_scripts.sh $SANDBOX_PATH;
            check_exit_status "Could not generate $DISTRIBUTION build scripts";
        else
            echo "Invalid distribution name: $DISTRIBUTION" >&2;
            exit 1;
        fi
        check_exit_status "Could not generate $DISTRIBUTION build scripts";
    fi
fi

if [[ $RUN_BUILD_COMMAND -eq 1 ]]; then
    echo "Running build command...";
    dpkg-buildpackage -b -uc
    check_exit_status "Build command encountered an error";
fi

cd "$CWD";

echo "Done";

