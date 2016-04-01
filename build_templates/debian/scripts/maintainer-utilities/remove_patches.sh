#!/bin/bash

source "$(dirname $(readlink -f $0))/quilt_variables.sh"
quilt pop -a
