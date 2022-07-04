#!/bin/fish

# Fish variant of set_quilt_vars.sh

alias quilt='quilt --quiltrc -'

set REPO_ROOT (dirname (dirname (readlink -f (status current-filename))))

set -gx QUILT_PATCHES "$REPO_ROOT/patches"

set -gx QUILT_PUSH_ARGS "--color=auto"
set -gx QUILT_DIFF_OPTS "--show-c-function"
set -gx QUILT_PATCH_OPTS "--unified --reject-format=unified"
set -gx QUILT_DIFF_ARGS "-p ab --no-timestamps --no-index --color=auto --sort"
set -gx QUILT_REFRESH_ARGS "-p ab --no-timestamps --no-index --sort --strip-trailing-whitespace"
set -gx QUILT_COLORS "diff_hdr=1;32:diff_add=1;34:diff_rem=1;31:diff_hunk=1;33:diff_ctx=35:diff_cctx=33"
set -gx QUILT_SERIES_ARGS "--color=auto"
set -gx QUILT_PATCHES_ARGS "--color=auto"

set -gx LC_ALL C
