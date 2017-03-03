# Sets quilt variables for updating the patches

export QUILT_PATCHES="ungoogled_patches/patches"
export QUILT_SERIES="../patch_order"
export QUILT_PATCH_OPTS="--reject-format=unified"
#export QUILT_DIFF_ARGS="-p ab --no-timestamps --no-index --color=auto"
#export QUILT_REFRESH_ARGS="-p ab --no-timestamps --no-index"
export QUILT_COLORS="diff_hdr=1;32:diff_add=1;34:diff_rem=1;31:diff_hunk=1;33:diff_ctx=35:diff_cctx=33"
export QUILT_NO_DIFF_TIMESTAMPS=1
export QUILT_NO_DIFF_INDEX=1
