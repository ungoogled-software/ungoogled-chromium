#!/bin/sh

# Set PATH variable to cmds/ directory on UNIX shell-compatible systems
# Run this script with "source" in order for the PATH variable to take effect
export PATH=$(dirname $(readlink -f $0))/cmds:$PATH
