# Design and implementation

Configuration flags, patches, and build script settings are stored in the `resources` directory. The `resources` directory contains the `common` directory, which has such files that apply to all platforms. All other directories, named by platform, contain additional platform-specific data. Most of the features, however, are stored in the `common` directory.

There are currently two source-processing scripts:
* Source cleaner - Used to clean out binary files (i.e. do not seem to be human-readable text files, except a few required for building)
* Domain substitution - Used to replace Google and other domains in the source code to eliminate communication not caught by the patches and build flags.

These processing scripts are a part of the build system.

## `buildlib`: The building system

ungoogled-chromium provides a flexible and extensible Python library called [`buildlib`](buildlib.py) that does source code downloading, source cleaning, domain substitution, patching, building, and packaging. There's no documentation on `buildlib` yet, but it's pretty straight-forward to use. See `build.py` for an example on using `buildlib`.

## General building steps used in `buildlib`

1. Get the source code archive in `.tar.xz` format via `https://commondatastorage.googleapis.com/` and extract it into `build/sandbox/`
    * Also download any additional non-Linux dependencies for building on non-Linux platforms, since the `.tar.xz` is generated on a Linux system
2. Run source cleaner (done during source archive extraction)
    * Optional, enabled by default
2. Run domain substitution
    * Optional, enabled by default
2. Copy patches into `build/patches/` and apply them
    * If domain substitution was run earlier, then the patches will pass through domain substitution first
3. Configure the build utilities and run meta-build configuration (i.e. GYP, not GN. See [Issue #16](//github.com/Eloston/ungoogled-chromium/issues/16))
4. Build (via 'ninja')
5. Generate binary packages and place them in `build/`

## Contents of the `resources` directory

* `cleaning_list` - (Used for source cleaning) A list of files to be excluded during the extraction of the Chromium source
* `domain_regex_list` - (Used for domain substitution) A list of regular expressions that define how domains will be replaced in the source code
* `domain_substitution_list` - (Used for domain substitution) A list of files that are processed by `domain_regex_list`
* `extra_deps.ini` - Contains info to download extra dependencies needed for the platform but not included in the main Chromium source archive
* `gn_args.ini` - A list of GN arguments to use for building. (Currently unused, see [Issue #16](//github.com/Eloston/ungoogled-chromium/issues/16))
* `gyp_flags` - A list of GYP flags to use for building.
* `patches/` - Contains patches. `common/patches` directory contains patches that provide the main features of ungoogled-chromium (as listed above) and can be applied on any platform (but are not necessarily designed to affect all platforms). However, other `patches/` directories in other platform directories are platform-specific. The contents of `common/patches` are explained more in-depth below.
    * `patch_order` - The order to apply the patches in. Patches from `common` should be applied before the one for a platform.

All of these files are human-readable, but they are usually processed by the Python building system. See the Building section below for more information.

## Contents of the `resources/common/patches` directory

* `debian/` - Contains patches from Debian's Chromium.
    * Patches are not touched unless they do not apply cleanly onto the version of Chromium being built
    * These patches are not Debian-specific. For those, see the `resources/debian/patches` directory
* `inox-patchset/` - Contains a modified subset of patches from Inox patchset.
    * Some patches such as those that change branding are omitted
    * Patches are not touched unless they conflict with Debian's patches
    * Patches are from [inox-patchset's GitHub](//github.com/gcarq/inox-patchset)
    * [Inox patchset's license](//github.com/gcarq/inox-patchset/blob/master/LICENSE)
* `iridium-browser` - Contains a modified subset of patches from Iridium Browser.
    * Some patches such as those that change branding or URLs to point to Iridium's own servers are omitted
    * Patches are not touched unless they conflict with Debian's or Inox's patches
    * Patches are from the `patchview` branch of Iridium's Git repository. [Git webview of the patchview branch](//git.iridiumbrowser.de/cgit.cgi/iridium-browser/?h=patchview)
* `ungoogled-chromium/` - Contains new patches for ungoogled-chromium. They implement the features described above.
