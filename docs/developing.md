# Development notes and procedures

This document contains an assortment of information for those who want to develop ungoogled-chromium.

Information targeted towards developers *and* other users live in [the Wiki](//ungoogled-software.github.io/ungoogled-chromium-wiki/).

## Branches

Development is focused on `master`, and any changes in there should not break anything unless platforms break during a Chromium version rebase.

Larger feature changes or hotfixes must be done in a separate branch. Once they are ready, then a Pull Request can be made onto `master` (for contributors with write access, merging directly via a git client is fine). After the branch is merged, it should be removed.

## Adding command-line flags and `chrome://flags` options

See `docs/how_to_add_your_feature_flag.md` in the Chromium source tree for the steps needed. Note that updating `tools/metrics/histograms/enums.xml` is not required.

For new flags, first add a constant to `third_party/ungoogled/ungoogled_switches.cc` (by modifying patch `resources/patches/ungoogled-chromium/add-third-party-ungoogled.patch`). Then, use this constant in the steps outlined above.

## Notes on updating bundles

* It is highly recommended to have a read through [docs/design.md](docs/design.md) *and* reference existing bundles to understand the divisions of configuration.
* Anytime the bundles or patches are modified, use `devutils/validate_config.py` to run several sanity checking algorithms.
* Whenever patch orders or patches are modified, use `devutils/validate_patches.py` for validation. See the following section for more details on updating patches.
* If you are rebasing patches against a new Chromium version, please add `patches_outdated = true` to the `bundlemeta.ini` of any config bundles that you are not able to update. This will prevent failing CI status checks until those bundles' patches have been updated.

## Workflow of updating patches

Tested on Debian 9.0 (stretch). Exact instructions should work on any other Linux or macOS system with the proper dependencies.

It is recommended to read the [docs/building.md](docs/building.md) and [docs/design.md](docs/design.md) documents first to gain a deeper understanding of the process.

### Dependencies

* [`quilt`](http://savannah.nongnu.org/projects/quilt)
    * This is available in most (if not all) Linux distributions, and also Homebrew on macOS.
    * This utility facilitates most of the updating process, so it is important to learn how to use this. The manpage for quilt (as of early 2017) lacks an example of a workflow. There are multiple guides online, but [this guide from Debian](https://wiki.debian.org/UsingQuilt) and [the referenced guide on that page](https://raphaelhertzog.com/2012/08/08/how-to-use-quilt-to-manage-patches-in-debian-packages/) are the ones referenced in developing the current workflow.
* Python 3.5 or newer

#### Steps for initial update

This is an example workflow on Linux that can be modified for your specific usage.

### Downloading the source code and updating lists

The utility `devutils/update_lists.py` automates this process. By default, it will update the `common` base bundle automatically. Pass in `-h` or `--help` for available options.

Here's an example for updating the `common` configuration type:

```
mkdir -p build/downloads
./devutils/update_lists.py --auto-download -c build/downloads -t build/src
```

The resulting source tree in `build/src` will not have binaries pruned or domains substituted.

#### Updating patches

**IMPORTANT**: Make sure domain substitution has not been applied before continuing. Otherwise, the resulting patches will require domain substitution.

1. Setup a source tree without domain substitution. For the `common` bundle:
    1. `python3 -m buildkit downloads retrieve -b config_bundles/common -c build/downloads`
    2. `python3 -m buildkit downloads unpack -b config_bundles/common -c build/downloads build/src`
2. Run `source devutils/set_quilt_vars.sh`
    * This will setup quilt to modify patches directly in `patches/`
3. If updating patches for a specific bundle, run `devutils/update_patches.py -as build/src` (if updating for a specific bundle, append `-b BUNDLE_PATH_HERE`). If successful, then everything is done. Otherwise, continue on to the next step.
4. Use `quilt` to fix the broken patch:
    1. Run `quilt push -f`
    2. Edit the broken files as necessary by adding (`quilt edit ...` or `quilt add ...`) or removing (`quilt remove ...`) files as necessary
        * When removing large chunks of code, remove each line instead of using language features to hide or remove the code. This makes the patches less susceptible to breakages when using quilt's refresh command (e.g. quilt refresh updates the line numbers based on the patch context, so it's possible for new but desirable code in the middle of the block comment to be excluded.). It also helps with readability when someone wants to see the changes made based on the patch alone.
    3. Refresh the patch: `quilt refresh`
    4. Run `devutils/update_patches.py -as build/src -b BUNDLE_PATH_HERE` (if updating a specific bundle, append `-b BUNDLE_PATH_HERE`). If successful, then continue on to the next step. Otherwise, repeat this procedure within Step 4 of the entire instructions.
5. Run `devutils/validate_config.py`
6. Run `quilt pop -a`
7. If updating patches for a specific bundle, run `devutils/validate_patches.py -l build/src` (if updating a specific bundle, append `-b BUNDLE_PATH_HERE`). If errors occur, go back to Step 3.

This should leave unstaged changes in the git repository to be reviewed, added, and committed.

If you used `quilt new` anywhere during the update process, remember to add that patch manually to the corresponding `patch_order.list` for the applicable bundle.

For bundles that you are not able to update, please add `patches_outdated = true` to the `bundlemeta.ini` for those corresponding config bundles. This will prevent failing CI status checks until those bundles' patches have been updated.

### Steps for fixing patches after a failed build attempt

If domain substitution is not applied, then the steps from the previous section will work for revising patches.

If domain substitution is applied, then the steps for the initial update will not apply since that would create patches which depend on domain substitution. Here is a method of dealing with this:

1. Revert domain substitution: `python3 -m buildkit domains revert -c CACHE_PATH_HERE build/src`
2. Follow the patch updating section above
3. Reapply domain substitution: `python3 -m buildkit domains apply -b BUNDLE_PATH_HERE -c CACHE_PATH_HERE build/src`
4. Reattempt build. Repeat steps as necessary.
