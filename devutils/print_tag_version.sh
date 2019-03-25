_root_dir=$(dirname $(dirname $(readlink -f $0)))
printf '%s-%s' $(cat $_root_dir/chromium_version.txt) $(cat $_root_dir/revision.txt)
