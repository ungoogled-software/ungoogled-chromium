# Building ungoogled-chromium

To build ungoogled-chromium, please consult [the repository for your supported platform (links here)](docs/platforms.md).

If your platform is not supported, or you want to customize your own build, you may have a look at the example below and the code for supported platforms.

## Rough example

Here is a rough example for building Chromium with only the changes from the main repository:

1. Download and unpack the source code:

```sh
./utils/downloads.py retrieve -c build/downloads_cache -i downloads.ini
./utils/downloads.py unpack -c build/downloads_cache -i downloads.ini build/src
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
./utils/domain_substitution.py apply -r domain_regex.list -f domain_substitution.list -c build/domsubcache.tar.gz
```

5. Build GN:

```sh
mkdir -p build/src/out/Default
cp flags.gn build/src/out/Default/args.gn
cd build/src
./tools/gn/bootstrap.py --skip-generate-buildfiles -j4 -o out/Default/gn
```

6. Build Chromium:

```
./out/Default/gn gen out/Default --fail-on-unused-args
ninja -C out/Default chrome chromedriver chrome_sandbox
```
