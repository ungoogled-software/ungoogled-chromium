# Sets quilt variables for updating the patches
# Make sure to run this with the shell command "source" in order to inherit the variables into the interactive environment

# Assumes the script is run from the repository
REPO_ROOT=$(dirname $(readlink -f $0))

export QUILT_PATCHES="$REPO_ROOT/resources/patches"
export QUILT_SERIES="$REPO_ROOT/buildspace/updating_patch_order.list"
# Options below borrowed from Debian
export QUILT_PATCH_OPTS="--reject-format=unified"
export QUILT_DIFF_ARGS="-p ab --no-timestamps --no-index --color=auto"
export QUILT_REFRESH_ARGS="-p ab --no-timestamps --no-index"
export QUILT_COLORS="diff_hdr=1;32:diff_add=1;34:diff_rem=1;31:diff_hunk=1;33:diff_ctx=35:diff_cctx=33"
#export QUILT_NO_DIFF_TIMESTAMPS=1
#export QUILT_NO_DIFF_INDEX=1
