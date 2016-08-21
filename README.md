# ungoogled-chromium

**A Google Chromium variant focusing on removing Google integration, enhancing privacy, and adding features**

### Features

In addition to features provided by [Iridium Browser](//iridiumbrowser.de/) and [Inox patchset](//github.com/gcarq/inox-patchset), the following is also included:
* Replace many web domains in the source code with non-existent alternatives ending in `qjz9zk` (known as domain substitution)
* Strip binaries from the source code (known as source cleaning)
    * This includes all pre-built executables, shared libraries, and other forms of machine code. They are substituted with system or user-provided equivalents, or built from source.
    * However some data files (e.g. `icudtl.dat` for Unicode and Globalization support and `*_page_model.bin` that define page models for the DOM Distiller) are left in as they do not contain machine code and are needed for building.
* Remove additional detection of and disable specific functionality for Google hosts
* Disable searching in Omnibox
* Disable automatic formatting of URL in Omnibox
* Disable JavaScript dialog boxes from showing when a page closes (onbeforeunload dialog boxes)
* Added menu item under "More tools" to clear the HTTP authentication cache on-demand
* Force all pop-ups into tabs
* Disable intranet redirect detector (unnecessary invalid DNS requests)
* Add more URL schemes allowed for saving
* (Iridium Browser feature change) Prevent URLs with the `trk:` scheme from connecting to the Internet
    * Also prevents any URLs with the top-level domain `qjz9zk` (as used in domain substitution) from attempting a connection.
* (Iridium and Inox feature change) Prevent pinging of IPv6 address when detecting the availability of IPv6
* Support for building Debian and Ubuntu packages
    * Creates a separate package `chrome-sandbox` for the SUID sandbox
* Windows support with additional changes:
    * Build `wow_helper.exe` from source instead of using the pre-built version
    * Build `swapimport.exe` from source instead of downloading it from Google (requires [customized syzygy source code](https://github.com/Eloston/syzygy))
    * Build `yasm.exe` from source instead of using the pre-built version
    * Use user-provided building utilities instead of the ones bundled with Chromium (currently `gperf` and `bison`)
    * Do not set the Zone Identifier on downloaded files (which is a hassle to unset)

**DISCLAIMER: Although it is the top priority to eliminate bugs and privacy-invading code, there will be those that slip by due to the fast-paced growth and evolution of the Chromium project.**

## Getting ungoogled-chromium

Users are encouraged to use [one of the available tag](//github.com/Eloston/ungoogled-chromium/tags) versions. Binaries are available on [the releases page](//github.com/Eloston/ungoogled-chromium/releases) for the corresponding tag.

Tags are formatted in the following manner: `{chromium_version}-{release_revision}` where

* `chromium_version` is the version of Chromium used in `x.x.x.x` format, and
* `release_revision` is an integer indicating the version of ungoogled-chromium for the corresponding Chromium version.

The `master` branch is for development, so it is not guaranteed to be in a working state.

Currently supported platforms and distributions:
* Debian
* Ubuntu
* Windows
* Mac OS

## ungoogled-chromium's design

Features are implemented through a combination of build flags, patches, and a few configuration files for scripts. All of these settings are stored in the `resources` directory. The `resources` directory contains the `common` directory, which has such files that apply to all platforms. All other directories, named by platform, contain additional platform-specific data. Most of the features, however, are stored in the `common` directory.

There are currently two automated scripts that process the source code:
* Source cleaner - Used to clean out binary files (i.e. do not seem to be human-readable text files, except a few required for building)
* Domain substitution - Used to replace Google and other domains in the source code to eliminate communication not caught by the patches and build flags.

These are the general steps that ungoogled-chromium takes to build:

1. Get the source code archive in `.tar.xz` format via https://commondatastorage.googleapis.com/
2. Run source cleaner (done during source archive extraction)
2. Run domain substitution
2. Apply patches
3. Configure the build utilities and run meta-build configuration (i.e. GYP, not GN. See [Issue #16](//github.com/Eloston/ungoogled-chromium/issues/16))
4. Build (via 'ninja')

Here's a breakdown of what is in a resources directory:
* `cleaning_list` - (Used for source cleaning) A list of files to be excluded during the extraction of the Chromium source
* `domain_regex_list` - (Used for domain substitution) A list of regular expressions that define how domains will be replaced in the source code
* `domain_substitution_list` - (Used for domain substitution) A list of files that are processed by `domain_regex_list`
* `gn_args.ini` - A list of GN arguments to use for building. (Currently unused, see [Issue #16](//github.com/Eloston/ungoogled-chromium/issues/16))
* `gyp_flags` - A list of GYP flags to use for building.
* `patches/` - Contains patches. `common/patches` directory contains patches that provide the main features of ungoogled-chromium (as listed above) and can be applied on any platform (but are not necessarily designed to affect all platforms). However, other `patches/` directories in other platform directories are platform-specific. The contents of `common/patches` are explained more in-depth below.
    * `patch_order` - The order to apply the patches in. Patches from `common` should be applied before the one for a platform.

All of these files are human-readable, but they are usually processed by the Python building system. See the Building section below for more information.

Here's a breakdown of the `common/patches` directory:
* `ungoogled-chromium/` - Contains new patches for ungoogled-chromium. They implement the features described above.
* `iridium-browser` - Contains a subset of patches from Iridium Browser.
    * Patches are not touched unless they do not apply cleanly onto the version of Chromium being built
    * Patches are from the `patchview` branch of Iridium's Git repository. [Git webview of the patchview branch](//git.iridiumbrowser.de/cgit.cgi/iridium-browser/?h=patchview)
* `inox-patchset/` - Contains a modified subset of patches from Inox patchset.
    * Patches are from [inox-patchset's GitHub](//github.com/gcarq/inox-patchset)
    * [Inox patchset's license](//github.com/gcarq/inox-patchset/blob/master/LICENSE)
* `debian/` - Contains patches from Debian's Chromium.
    * These patches are not Debian-specific. For those, see the `resources/debian/patches` directory

## Building

[See BUILDING.md](BUILDING.md)

## Contributing

Contributers are welcome!

Use the [Issue Tracker](//github.com/Eloston/ungoogled-chromium/issues) for problems, suggestions, and questions.

### Pull requests

Pull requests are also welcome. Here are some guidelines:
* Changes that fix certain configurations or add small features and do not break compatibility are generally okay
* Larger changes, such as those that change `buildlib`, should be proposed through an issue first before submitting a pull request.
* When in doubt, propose the idea through an issue first.

## Credits

[Iridium Browser](//iridiumbrowser.de/)

[Inox patchset](//github.com/gcarq/inox-patchset)

[Debian for build scripts](//tracker.debian.org/pkg/chromium-browser)

[The Chromium Project](//www.chromium.org/)

## License

GPLv3. See [LICENSE](LICENSE)
