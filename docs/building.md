# Building ungoogled-chromium

The recommended way to build ungoogled-chromium is by consulting [the repository for your supported platform (links here)](platforms.md).

* *Linux users*: If your distribution is not listed, you will need to use Portable Linux.

If you want to add ungoogled-chromium to your existing Chromium build process, see the next section. Additionally, you may reference the repositories for supported platforms for inspiration.

## Integrating ungoogled-chromium into your Chromium build process

Typically, ungoogled-chromium is built from [code in platform-specific repositories](platforms.md). However, ungoogled-chromium can also be included in part or in whole into any custom Chromium build. In this section, **we will assume you already have a process to make your own Chromium builds**.

**NOTE**: You may need additional patches and/or build configuration for [your supported platform](platforms.md) because this repository does not contain all the code necessary for all platforms.

Before continuing, you may find it helpful to have a look through [the design documentation](design.md).

The following procedure outline the essential steps to build Chromium will all of ungoogled-chromium's features. **They are not sufficient to build ungoogled-chromium on their own**.

1. Ensure Chromium is downloaded, such as by `depot_tools`. In most of our supported platforms, we instead use a custom tool to do this.

```sh
mkdir -p build/download_cache
./utils/downloads.py retrieve -c build/download_cache -i downloads.ini
./utils/downloads.py unpack -c build/download_cache -i downloads.ini -- build/src
```

2. Prune binaries

```sh
./utils/prune_binaries.py build/src pruning.list
```

3. Apply patches

```sh
./utils/patches.py apply build/src patches
```

4. Substitute domains

```sh
./utils/domain_substitution.py apply -r domain_regex.list -f domain_substitution.list -c build/domsubcache.tar.gz build/src
```

5. Build GN. If you are using `depot_tools` to checkout Chromium or you already have a GN binary, you should skip this step.

```sh
mkdir -p build/src/out/Default
cd build/src
./tools/gn/bootstrap/bootstrap.py --skip-generate-buildfiles -j4 -o out/Default/
```

6. Invoke the build:

```
mkdir -p build/src/out/Default
# NOTE: flags.gn contains only a subset of what is needed to run the build.
cp flags.gn build/src/out/Default/args.gn
cd build/src
# If you have additional GN flags to add, make sure to add them now.
./out/Default/gn gen out/Default --fail-on-unused-args
ninja -C out/Default chrome chromedriver chrome_sandbox
```

## Building FAQ

### My build keeps crashing because I run out of RAM! How can I fix it?

Here are several ways to address this, in decreasing order of preference:

1. Decrease the number of parallel threads to Ninja (the `-j` flag)
2. Add swap space
