# Building ungoogled-chromium

**Notice for master branch users**: The information in this document may not apply to the latest tag version. Please consult the documentation from the tag instead.

## Common building requirements

The following is needed to fully use `utilikit`:
* Python 3 (tested on 3.5) for running `utilikit`
* The following can be provided by [Google's depot_tools](//www.chromium.org/developers/how-tos/install-depot-tools) (but it is recommended to obtain these from their respective websites)
    * Python 2 (tested on 2.7) for building GN and running other scripts
    * [Ninja](//ninja-build.org/) for running the build command

Additional requirements are listed in the sections for specific platforms.

## General building instructions

Here are the general steps for building a package of ungoogled-chromium:

* Set `UTILIKIT_*` environment variables
* Check to see if the build environment is setup correctly: `utilikit/check_requirements.py`
* Make build directories `build/`, `build/sandbox/`, `build/downloads/`
* Prepare the source code: `utilikit/prepare_sources.py`
* Apply domain substitution: `utilikit/substitute_domains.py`
* Generate a build script: `utilikit/generate_build_files.py`
* Invoke the build script

All build scripts follow the general pattern:
* Setup some or all of the source tree (as necessary)
* Apply patches
* Build GN via `tools/gn/bootstrap/bootstrap.py`
* Run `gn gen` with the GN flags
* Build Chromium via `ninja`

All utilities in `utilikit` have built-in command-line help. Pass in `-h` or `--help` for details.

If you just want the build flags and patches without going through `utilikit`, you can use `utilikit/export_resources.py` to export them.

The general building steps is only one use case of `utilikit`. You can use whichever and as many utilities as needed in your build process.

For a list of all `utilikit` utilities, see [DESIGN.md](DESIGN.md).

### Configuring environment variables

`utilikit` uses a few environment variables to reduce redundancy in command invocations.

Here is a list of variables:
* `UTILIKIT_CONFIG_TYPE` - The configuration to use. This corresponds to a directory name in `resources/configs`
* `UTILIKIT_RESOURCES` - The path to the `resources` directory. Defaults to `../resources`, relative to the `utilikit` directory.
* `UTILIKIT_DOWNLOADS_DIR` - The path containing downloaded Chromium source archive and other packed dependencies. Defaults to `../build/downloads`, relative to the `utilikit` directory.
* `UTILIKIT_SANDBOX_DIR` - The path containing the build sandbox. Defaults to `../build/sandbox`, relative to the `utilikit` directory.

For Linux users, make sure to `export` these variables to make them available to sub-processes.

## Platform-specific building instructions

### Debian and derivatives

These build instructions should work on the CPU architectures `amd64`, `i386`, `arm64`, and `armhf`.

Install common requirements: `# apt install packaging-dev python3 python2 ninja`

For Debian 9 (stretch):

```
export UTILIKIT_CONFIG_TYPE=debian_stretch
./utilikit/check_requirements.py --common --quilt
mkdir build/
mkdir build/sandbox
mkdir build/downloads
./utilikit/prepare_sources.py
./utilikit/substitute_domains.py
./utilikit/generate_build_files.py debian --flavor standard --apply-domain-substitution
dpkg-checkbuilddeps # Checks and reports any additional packages needed
cd build/sandbox
dpkg-buildpackage -b -uc
```

Packages will appear under `build/`.

Deviations for different Debian versions or flavors:

Ubuntu 16.04 (xenial) and Debian 8 (jessie):
* Set `UTILIKIT_CONFIG_TYPE=linux_conservative`
* Use `--flavor conservative` in `generate_build_files.py`

### Windows

**These instructions are out-of-date**

Google only supports [Windows 7 x64 or newer](https://chromium.googlesource.com/chromium/src/+/51.0.2704.106/docs/windows_build_instructions.md#Setting-up-the-environment-for-Visual-Studio). These instructions are tested on Windows 10 Home x64.

For maximum portability, the build configuration will generate x86 binaries by default. This can be changed to x64 by setting `builder.target_cpu = CPUArch.x64` in `build.py`.

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

See `build.py` for more on customizing the build environment or process.

#### Build

To make sure that the GN tool builds correctly, make sure you run `vcvarsall` in the build command-line with the correct arguments:
* `vcvarsall amd64_x86` for building x86 binaries
* `vcvarsall amd64` for building x64 binaries

Then do the following:

    # Change directory to ungoogled-chromium's root directory
    path\to\python3 build.py

### macOS

**These instructions are out-of-date**

**NOTE: There is no official maintainer for this platform. If there is a problem, please submit a pull request or issue**

Tested on macOS 10.11.6

Credits to [9Morello](//github.com/9Morello) for most of the work done on this platform.

#### Additional Requirements

* Xcode 7
* Homebrew
* Perl (for creating a `.dmg` package)

#### Setting up the build environment

1. Install Quilt via Homebrew: `brew install quilt`
2. Install Ninja via Homebrew: `brew install ninja`

See `build.py` for more on customizing the build environment or process.

#### Build

# Change directory to ungoogled-chromium's root directory

```
export UTILIKIT_CONFIG_TYPE=macos
./utilikit/check_requirements.py --common --quilt --macos
mkdir build/
mkdir build/sandbox
mkdir build/downloads
./utilikit/prepare_sources.py
./utilikit/substitute_domains.py
./utilikit/generate_build_files.py macos --apply-domain-substitution
cd build/sandbox
quilt push -a
./tools/gn/bootstrap/bootstrap.py -v
./out/Release/gn gen out/Release  --fail-on-unused-args
```
####Modify args.gn inside out/Release to look like this
```
is_debug = false
treat_warnings_as_errors=false
fatal_linker_warnings=false
use_ozone=false
use_sysroot=false
enable_remoting=false
enable_nacl=false
enable_nacl_nonsfi=false
safe_browsing_mode=0
enable_webrtc=false
enable_hangout_services_extension=false
fieldtrial_testing_like_official_build=true
proprietary_codecs=true
ffmpeg_branding="Chrome"
enable_google_now=false
enable_one_click_signin=false
enable_hotwording=false
google_api_key=""
google_default_client_id=""
google_default_client_secret=""
use_official_google_api_keys=false
remove_webcore_debug_symbols=true
enable_widevine=true
symbol_level=0
enable_iterator_debugging=false
```
#####and finally:
```
ninja -C out/Release chrome
```


### Arch Linux

**This is a WIP**

For now, see the instructions for Other Linux distributions. The resulting binary will still use system libraries.

### Other Linux distributions

**These instructions are out-of-date**

#### Setting up the build environment

* Install the following through your package manager or elsewhere:
    * `clang`, preferrably the latest version
    * Python 3.5 or newer (or 3.4 if necessary)
    * Python 2
    * `quilt`
    * `ninja`
* Follow [these instructions](//chromium.googlesource.com/chromium/src/+/55.0.2883.75/docs/linux_build_instructions.md#Install-additional-build-dependencies) to install additional dependencies for building

#### Build

    # Change directory to ungoogled-chromium's root directory
    python3 build.py

### Notes for other systems, platforms, and configurations

You may find [DESIGN.md](DESIGN.md) a helpful read.

Consult the build instructions on the [Chromium homepage](//www.chromium.org/Home) for platform-specific building information.

You can use `depot_tools` to setup the Chromium source tree in `build/sandbox` if `utilikit`'s source downloading system does not support a configuration. However, please note that this will involve executing Google binaries part of `depot_tools` and will run scripts that can download and run more Google binaries.

The main set of patches (listed in `resources/configs/common/patch_order`) should work on most, if not all, platforms supported by desktop Chromium. Some patches are there to fix building with certain build flags, so those may not work with other platforms or configurations. However, the patches as they are should apply as long as there is a clean and unmodified source tree.

Domain substitution and source cleaning will break scripts that downloads from Google, and other scripts operating on binary files from the source tree.
