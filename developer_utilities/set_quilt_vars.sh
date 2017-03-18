# Sets quilt variables for updating the patches
# Make sure to run this with the shell command "source" in order to inherit the variables into the interactive environment
# Requires the absolute path to the repository root directory as the argument

export QUILT_PATCHES="$1/resources/patches"
export QUILT_SERIES="$1/build/updating_patch_order"
export QUILT_PATCH_OPTS="--reject-format=unified"
#export QUILT_DIFF_ARGS="-p ab --no-timestamps --no-index --color=auto"
#export QUILT_REFRESH_ARGS="-p ab --no-timestamps --no-index"
export QUILT_COLORS="diff_hdr=1;32:diff_add=1;34:diff_rem=1;31:diff_hunk=1;33:diff_ctx=35:diff_cctx=33"
export QUILT_NO_DIFF_TIMESTAMPS=1
export QUILT_NO_DIFF_INDEX=1
