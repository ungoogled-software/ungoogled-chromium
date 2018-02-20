# Windows MSYS2 script to apply patches via quilt

mv $(dirname $(readlink -f $0))/patches ./

alias quilt='quilt --quiltrc -'

export QUILT_PATCH_OPTS="-p 1 --reject-format=unified"
export QUILT_COLORS="diff_hdr=1;32:diff_add=1;34:diff_rem=1;31:diff_hunk=1;33:diff_ctx=35:diff_cctx=33"
export QUILT_DIFF_ARGS="-p ab --no-timestamps --no-index --color=auto"
export QUILT_REFRESH_ARGS="-p ab --no-timestamps --no-index"

quilt push -a
