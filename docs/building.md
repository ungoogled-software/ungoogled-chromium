# Building ungoogled-chromium

The recommended way to build ungoogled-chromium is by consulting [the repository for your supported platform (links here)](platforms.md).

* *Linux users*: If your distribution is not listed, you will need to use Portable Linux.

If you want to know how to use ungoogled-chromium's build process in your own Chromium builds, you may have a look at the rough example below. Additionally, you may reference the repositories for supported platforms for inspiration.

## Rough example

**NOTE: This example is intended only for users who want to learn how ungoogled-chromium's build process works.** If you are simply trying to build and run ungoogled-chromium, please consult the [repository for your supported platform](platforms.md).

In order to get a working build from this example, you will need to develop your own build process. **This may be a time-consuming process.** Before continuing, you should be familiar with the [standard Chromium build process](https://chromium.googlesource.com/chromium/src/+/lkgr/docs/get_the_code.md), and [ungoogled-chromium's design documentation](design.md).

The following example demonstrates a typical build process. Please note that these steps alone will probably not be sufficient to get a working build.

1. Download and unpack the source code:

```sh
mkdir -p build/download_cache
./utils/downloads.py retrieve -c build/download_cache -i downloads.ini
./utils/downloads.py unpack -c build/download_cache -i downloads.ini -- build/src
```

2. Prune binaries: 

```sh
./utils/prune_binaries.py build/src pruning.list
```

3. Apply patches:

```sh
./utils/patches.py apply build/src patches
```

4. Substitute domains:

```sh
./utils/domain_substitution.py apply -r domain_regex.list -f domain_substitution.list -c build/domsubcache.tar.gz build/src
```

5. Build GN:

```sh
mkdir -p build/src/out/Default
cp flags.gn build/src/out/Default/args.gn
cd build/src
./tools/gn/bootstrap/bootstrap.py --skip-generate-buildfiles -j4 -o out/Default/gn
```

6. Build Chromium:

```
./out/Default/gn gen out/Default --fail-on-unused-args
ninja -C out/Default chrome chromedriver chrome_sandbox
```

## Building FAQ

### My build keeps crashing because I run out of RAM! How can I fix it?

Here are several ways to address this, in decreasing order of preference:

1. Set the GN flag `jumbo_file_merge_limit` to a lower value. At the time of writing, Debian uses `8` (the default varies, but it can be a higher value like `50`)
2. Decrease the number of parallel threads to Ninja (the `-j` flag)
3. Add swap space
