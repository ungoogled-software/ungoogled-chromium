# Building ungoogled-chromium

## IMPORTANT - Please read this section first

**Statuses of platform support**: Because platform support varies across stable versions, [this Wiki page tracks platform support for the current stable](//github.com/Eloston/ungoogled-chromium/wiki/statuses)

**Choosing branches**: The `master` branch contains stable code, and `develop` is for unstable code. Please do not use `develop` unless you know what you are doing.

## Contents

There are two major sections of this document:

* [Platform-specific building instructions](#platform-specific-building-instructions) - For users who are using a supported platform and don't need to customize their build.
* [Building generalizations and additional information](#building-generalizations-and-additional-information) - For users who are building for a platform without build instructions or who need additional customizations.

## Platform-specific building instructions

This section is for users who are using a supported platform and don't need to customize their build.

These instructions are the ones used for producing the published binaries.

### Debian and its derivatives

These instructions will create `.deb` packages using ungoogled-chromium's variation of Debian's `debian` directory.

The build should work on the CPU architectures `amd64`, `i386`, `arm64`, and `armhf`.

The final size of the sandbox with build artifacts is over 5 GB. On systems with enough RAM, it can be built entirely within `tmpfs` without swap memory.

Install common requirements: `# apt install packaging-dev python3 python2 ninja-build`

For Debian 9 (stretch):

```
export UTILIKIT_CONFIG_TYPE=debian_stretch
mkdir build/
mkdir build/sandbox
mkdir build/downloads
./utilikit/prepare_sources.py
./utilikit/substitute_domains.py
./utilikit/generate_build_files.py debian --flavor standard --apply-domain-substitution
cd build/sandbox
dpkg-checkbuilddeps # Checks and reports any additional packages needed
dpkg-buildpackage -b -uc
```

Packages will appear under `build/`.

Deviations for different Debian versions or flavors:

Ubuntu 17.04 (zesty): Same as Debian 9 (stretch)

Ubuntu 16.04 (xenial):
* Set `UTILIKIT_CONFIG_TYPE=linux_portable`
* Use `--flavor minimal` in `generate_build_files.py`

Debian 8.0 (jessie) is currently not working at this time, due to `utilikit` using Python 3.5 features and the lack of a build configuration that will work on it.

Other versions or derivatives are not officially supported, but it still may be possible to build on them with the settings from one listed above.

### Windows

**These instructions are out-of-date**

Google only supports [Windows 7 x64 or newer](https://chromium.googlesource.com/chromium/src/+/51.0.2704.106/docs/windows_build_instructions.md#Setting-up-the-environment-for-Visual-Studio). These instructions are tested on Windows 10 Home x64.

For maximum portability, the build configuration will generate x86 binaries by default. This can be changed to x64 by setting TODO

#### Additional Requirements
* Visual Studio. See [Chromium's Windows Build Instructions](https://chromium.googlesource.com/chromium/src/+/51.0.2704.106/docs/windows_build_instructions.md) for Google's requirements
    * Build has been tested on 2015 Community Edition Update 2 with only the following features installed:
        * Programming Languages -> Visual C++ (including all subcomponents)
        * Universal Windows App Development Tools -> Windows 10 SDK 10.0.10586
        * Windows 8.1 and Windows Phone 8.0/8.1 Tools -> Tools and Windows SDKs
* GNU patch (to deal with patches that have fuzz). You can get the latest GNU patch from [MSYS2](http://msys2.github.io/).
    * If you don't want to use the installer, you can download and extract the following files manually from [MSYS2's repository on SourceForge](https://sourceforge.net/projects/msys2/files/REPOS/MSYS2/x86_64/):
        * `/usr/bin/patch.exe` from `patch-*-x86_64.pkg.tar.xz`
        * `/usr/bin/msys-2.0.dll` from `msys2-runtime-*-x86_64.pkg.tar.xz`
        * These files are portable.
* [gperf from GNUWin32](http://gnuwin32.sourceforge.net/packages/gperf.htm)
* [bison from GNUWin32](http://gnuwin32.sourceforge.net/packages/bison.htm)
    * Get the Binaries, Developer files, Sources, and Dependencies
    * **NOTE**: Make sure to place gperf and bison in a path without spaces, otherwise the build will fail.

#### Setting up the build environment

Make sure the following are accessible in `PATH` (the PATH overrides feature can be used on the directories containing the actual executable):
* Python 2 as `python`
* Ninja as `ninja`
* GNU patch as `patch`
* gperf as `gperf`
* bison as `bison`

#### Build

To make sure that the GN tool builds correctly, make sure you run `vcvarsall` in the build command-line with the correct arguments:
* `vcvarsall amd64_x86` for building x86 binaries
* `vcvarsall amd64` for building x64 binaries

Then do the following:

TODO

### macOS

**NOTE: There is no official maintainer for this platform. If there is a problem, please submit a pull request or issue**

Tested on macOS 10.11-10.13

Credits:
* [9Morello](//github.com/9Morello)
* [tectiv3](//github.com/tectiv3)
* [nixballs](//github.com/nixballs)

#### Additional Requirements

* Xcode 7-9
* Homebrew
* Perl (for creating a `.dmg` package)

#### Setting up the build environment

1. Install Quilt via Homebrew: `brew install quilt`
2. Install Ninja via Homebrew: `brew install ninja`

#### Build

```
export UTILIKIT_CONFIG_TYPE=macos
./utilikit/check_requirements.py --macos
mkdir -p build/{sandbox,downloads}
./utilikit/prepare_sources.py
./utilikit/substitute_domains.py
./utilikit/generate_build_files.py macos --apply-domain-substitution
cd build/sandbox
./ungoogled_macos/build.sh
```

### Arch Linux

**This is a WIP**

For now, see the instructions for Other Linux distributions. The resulting binary will still use system libraries.

### Other Linux distributions

#### Setting up the build environment

TODO

#### Build

TODO

### Notes for other systems, platforms, and configurations

There is much freedom in building Chromium with ungoogled-chromium's changes. One may choose to abide more by ungoogled-chromium's general building steps (described in the or more by Google's steps for building Chromium.

[DESIGN.md](DESIGN.md) may be a helpful read to gain insights into `utilikit` and the project's file structure.

Consult the build instructions on the [Chromium homepage](//www.chromium.org/Home) for platform-specific building information.

You can use `depot_tools` to setup the Chromium source tree in `build/sandbox` if `utilikit`'s source downloading system does not support a configuration. However, please note that this will involve executing Google binaries part of `depot_tools` and will run scripts that can download and run more Google binaries.

The main set of patches (listed in `resources/configs/common/patch_order`) should work on most, if not all, platforms supported by desktop Chromium. Some patches are there to fix building with certain build flags, so those may not work with other platforms or configurations. However, the patches as they are should apply as long as there is a clean and unmodified source tree.

Domain substitution and source cleaning will break scripts that downloads from Google, and other scripts operating on binary files from the source tree.

## Building generalizations and additional information

This section is targeted towards users who are building for a platform without build instructions or who need additional customizations.

### Common building requirements

The following is needed to fully use `utilikit`:
* Python 3 (tested on 3.5) for running `utilikit`
* Python 2 (tested on 2.7) for building GN and running other scripts
* [Ninja](//ninja-build.org/) for running the build command

Alternatively, one can obtain Python 2 and Ninja binaries from [Google's depot_tools](//www.chromium.org/developers/how-tos/install-depot-tools). depot_tools provides additional utilities that may ease the setup of the build environment for certain target configurations.

Additional requirements are listed in the sections for specific platforms.

### Configuring environment variables

`utilikit` uses a few environment variables to reduce redundancy in command invocations.

Here is a list of variables:
* `UTILIKIT_CONFIG_TYPE` - The configuration to use. This corresponds to a directory name in `resources/configs`
* `UTILIKIT_RESOURCES` - The path to the `resources` directory. Defaults to `../resources`, relative to the `utilikit` directory.
* `UTILIKIT_DOWNLOADS_DIR` - The path containing downloaded Chromium source archive and other packed dependencies. Defaults to `../build/downloads`, relative to the `utilikit` directory.
* `UTILIKIT_SANDBOX_DIR` - The path containing the build sandbox. Defaults to `../build/sandbox`, relative to the `utilikit` directory.

For Linux users, make sure to `export` these variables to make them available to sub-processes.

### General building instructions

These steps are employed in the [platform-specific building instructions](#platform-specific-building-instructions) below. Do note, however, that this is only one application of `utilikit`.

If you just want the build flags and patches without going through `utilikit`, you can use `utilikit/export_resources.py` to export them.

Here is a typical build sequence for ungoogled-chromium:

1. Set `UTILIKIT_*` environment variables
2. Check to see if the build environment is setup correctly (optional, only certain requirements): `utilikit/check_requirements.py`
3. Make build directories `build/`, `build/sandbox/`, `build/downloads/`
4. Prepare the source code: `utilikit/prepare_sources.py`
5. Apply domain substitution: `utilikit/substitute_domains.py`
6. If `utilikit` can generate build files for the desired configuration, use the following:
    * Generate build files: `utilikit/generate_build_files.py`
    * Use the build files.
    * NOTE: The generated build files vary in format across configurations. Consult the [platform-specific building instructions](#platform-specific-building-instructions) below for usage details.
7. If not using generated build files, run the build sequence as follows:
    2. Apply patches
    3. Build GN via `tools/gn/bootstrap/bootstrap.py`
    4. Run `gn gen` with the GN flags
    5. Build Chromium via `ninja`
    6. Package the build outputs. This should be the same as it is for regular Chromium.

It should be noted that the build sequence...

* is similar to Google's build steps for Chromium, and identical to the steps used by some Linux packagers of Chromium.
* is automated by the build files.

All utilities in `utilikit` have built-in command-line help. Pass in `-h` or `--help` for details.

For a list of all `utilikit` utilities, see [DESIGN.md](DESIGN.md).
