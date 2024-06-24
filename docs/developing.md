# Development notes and procedures

This document contains an assortment of information for those who want to develop ungoogled-chromium.

Information targeted towards developers *and* other users live in [the Wiki](https://ungoogled-software.github.io/ungoogled-chromium-wiki/).

Contents:

* [Branches](#branches)
* [Adding command-line flags and chrome://flags options](#adding-command-line-flags-and-chromeflags-options)
* [Workflow of updating to a new Chromium version](#workflow-of-updating-to-a-new-chromium-version)

## Branches

Development is focused on `master`, and any changes in there should not break anything unless platforms break during a Chromium version rebase.

Larger feature changes or hotfixes must be done in a separate branch. Once they are ready, then a Pull Request can be made onto `master` (for contributors with write access, merging directly via a git client is fine). After the branch is merged, it should be removed.

## Adding command-line flags and `chrome://flags` options

See `docs/how_to_add_your_feature_flag.md` in the Chromium source tree for the steps needed. Note that updating `tools/metrics/histograms/enums.xml` is not required.

For new flags, first add a constant to `third_party/ungoogled/ungoogled_switches.cc` (by modifying patch `resources/patches/ungoogled-chromium/add-third-party-ungoogled.patch`). Then, use this constant in the steps outlined above.

## Workflow of updating to a new Chromium version

Tested on Debian 10 (buster). Exact instructions should work on any other Linux or macOS system with the proper dependencies.

To gain a deeper understanding of this updating process, have a read through [docs/design.md](design.md).

### Dependencies

* [`quilt`](http://savannah.nongnu.org/projects/quilt)
    * This is available in most (if not all) Linux distributions, and also Homebrew on macOS.
    * This utility facilitates most of the updating process, so it is important to learn how to use this. The manpage for quilt (as of early 2017) lacks an example of a workflow. There are multiple guides online, but [this guide from Debian](https://wiki.debian.org/UsingQuilt) and [the referenced guide on that page](https://raphaelhertzog.com/2012/08/08/how-to-use-quilt-to-manage-patches-in-debian-packages/) are the ones referenced in developing the current workflow.
* Python 3.9 or newer
    * `httplib2` and `six` are also required if you wish to utilize a source clone instead of the source tarball.

### Downloading the source code

#### Source tarball download (recommended):
```sh
mkdir -p build/download_cache
./utils/downloads.py retrieve -i downloads.ini -c build/download_cache
./utils/downloads.py unpack -i downloads.ini -c build/download_cache build/src
```

#### Source clone:
```sh
./utils/clone.py -o build/src
```

### Updating lists

The utility `devutils/update_lists.py` automates this process. By default, it will update the files in the local repo. Pass in `-h` or `--help` for available options.

```sh
./devutils/update_lists.py -t build/src
```

The resulting source tree in `build/src` *will not* have binaries pruned or domains substituted.

### Updating patches

**IMPORTANT**: Make sure domain substitution has not been applied before updating patches.

1. Run `source devutils/set_quilt_vars.sh` (or `source devutils/set_quilt_vars.fish` if you are using the fish shell)
    * This will setup quilt to modify patches directly in `patches/`
2. Go into the source tree: `cd build/src`
3. Use `quilt` to refresh all patches: `quilt push -a --refresh`
	* If an error occurs, go to the next step. Otherwise, skip to Step 5.
4. Use `quilt` to fix the broken patch:
    1. Run `quilt push -f`
    2. Edit the broken files as necessary by adding (`quilt edit ...` or `quilt add ...`) or removing (`quilt remove ...`) files as necessary
        * When removing large chunks of code, remove each line instead of using language features to hide or remove the code. This makes the patches less susceptible to breakages when using quilt's refresh command (e.g. quilt refresh updates the line numbers based on the patch context, so it's possible for new but desirable code in the middle of the block comment to be excluded.). It also helps with readability when someone wants to see the changes made based on the patch alone.
    3. Refresh the patch: `quilt refresh`
    4. Go back to Step 3.
5. Run `quilt pop -a`
6. Go back to ungoogled-chromium repo: `cd ../..`
7. Run `devutils/validate_config.py`. If any warnings are printed, address them; otherwise, continue to Step 8.
8. Run `devutils/validate_patches.py -l build/src`. If errors occur, go back to Step 3.

This should leave unstaged changes in the git repository to be reviewed, added, and committed.

### Steps for fixing patches after a failed build attempt

If domain substitution is not applied, then the steps from the previous section will work for revising patches.

If domain substitution is applied, then the steps for the initial update will not apply since that would create patches which depend on domain substitution. Here is a method of dealing with this:

1. Revert domain substitution: `./utils/domain_substitution.py revert -c CACHE_PATH_HERE build/src`
2. Follow the patch updating section above
3. Reapply domain substitution: `./utils/domain_substitution.py apply -r domain_regex.list -f domain_substitution.list -c CACHE_PATH_HERE build/src`
4. Reattempt build. Repeat steps as necessary.

### Next steps

* Submit a Pull Request of these changes to the ungoogled-chromium repo.
* Once the PR is merged, update the repositories of each platform repository that you are maintaining under the `ungoogled-software` organization.
