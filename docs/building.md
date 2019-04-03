# Building ungoogled-chromium

**NOTICE (2019-03-22): Not all platforms are updated yet. If your platform is not updated yet, please use the instructions and code in tag 72.0.3626.122-2**

The recommended way to build ungoogled-chromium is by consulting [the repository for your supported platform (links here)](platforms.md).

* *Linux users*: If your distribution is not listed, you will need to use Portable Linux.

If you want to make a custom build, you will need to develop your own build process. *Beware that this may be a time-consuming process.* The easiest way to do this is to modify an existing platform's code, like Portable Linux. Additionally, you may have a look at the example below for some inspiration.

## Rough example

**NOTE: This example is intended only for users who want to make a custom build.** If you are trying to build for a supported platform, please consult the [repository for your supported platform](platforms.md).

In order to get a working build from this example, you will need to develop your own build process. **This may be a time-consuming process.** Before continuing, you should be familiar with the [standard Chromium build process](https://chromium.googlesource.com/chromium/src/+/lkgr/docs/get_the_code.md), and [ungoogled-chromium's design documentation](design.md).

The following example demonstrates a typical build process. Please note that these steps alone may not be sufficient to get a working build.

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
