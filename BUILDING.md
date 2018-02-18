# Building ungoogled-chromium

## IMPORTANT - Please read this section first

**Statuses of platform support**: Because platform support varies across stable versions, [this Wiki page tracks platform support for the current stable](//github.com/Eloston/ungoogled-chromium/wiki/statuses)

**Choosing branches**: The `master` branch contains stable code, and `develop` is for unstable code. Please do not use `develop` unless you know what you are doing.

## Contents

There are two major sections of this document:

* [Standard building instructions](#standard-building-instructions) contains standard building instructions for supported platforms.
* [Advanced building information](#advanced-building-information) - For users who are building on unsupported systems or want a rough overview of the building procedure.

## Standard building instructions

This section contains standard building instructions for supported platforms.

Contents:

* [Debian and its derivatives](#debian-and-its-derivatives)
* [Windows](#windows)
* [macOS](#macos)
* [Arch Linux](#arch-linux)
* [Other Linux distributions](#other-linux-distributions)

### Debian and its derivatives


These instructions will create `.deb` packages. It uses ungoogled-chromium's variation of Debian's `debian` directory.

The build should work on the CPU architectures `amd64`, `i386`, `arm64`, and `armhf`.

The final size of the sandbox with build artifacts is over 5 GB. On systems with enough RAM, it can be built entirely within `tmpfs` without swap memory.

#### Setting up the build environment

Install base requirements: `# apt install packaging-dev python3 ninja-build`

On Debian 9 (stretch), `stretch-backports` APT source is used to obtain LLVM 5.0.

#### Setting up the buildspace tree and packaging files

Procedure for Debian 9 (stretch):

```
mkdir -p buildspace/downloads # Alternatively, buildspace/ can be a symbolic link
./buildkit-launcher.py genbun debian_stretch
./buildkit-launcher.py getsrc
./buildkit-launcher.py subdom
./buildkit-launcher.py genpkg debian --flavor standard
```
TODO: Investigate using dpkg-source to build a source package

The buildspace tree can be relocated to another system for building if necessary.

#### Invoking build

```
cd buildspace/tree
# Use dpkg-checkbuilddeps (from dpkg-dev) or mk-build-deps (from devscripts) to check for additional packages.
dpkg-buildpackage -b -uc
```

Packages will appear under `buildspace/`.

#### Notes for Debian derivatives

Ubuntu 17.10 (artful): Same as Debian 9 except the `ubuntu_artful` base bundle is used.

Ubuntu 16.04 (xenial), Debian 8.0 (jessie), and other older versions: See [Other Linux distributions](#other-linux-distributions)

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

#### Additional Requirements

* Xcode 7-9
* Homebrew
* Perl (for creating a `.dmg` package)

#### Setting up the build environment

1. Install Quilt via Homebrew: `brew install quilt`
2. Install Ninja via Homebrew: `brew install ninja`
3. Install GNU coreutils (for `greadlink` in packaging script): `brew install coreutils`

#### Setting up the buildspace tree and packaging files

```
mkdir -p buildspace/downloads # Alternatively, buildspace/ can be a symbolic link
./buildkit-launcher.py genbun macos
./buildkit-launcher.py getsrc
./buildkit-launcher.py subdom
./buildkit-launcher.py genpkg macos
```

The buildspace tree can be relocated to another system for building if necessary.

#### Invoking build

```
cd buildspace/tree
./ungoogled_packaging/build.sh
```

A `.dmg` should appear in `buildspace/`

### Arch Linux

**This is a WIP**

For now, see the instructions for Other Linux distributions.

### Other Linux distributions

These are for building on Linux distributions that do not have support already. It builds without distribution-optimized flags and patches for maximum compatibility.

#### Requirements

Debian-based: `# apt install packaging-dev python3 ninja-build`

* If not building a `.deb` package, replace `packaging-dev` with `quilt python clang llvm-dev`

Other:

* Python 3 (tested on 3.5) for buildkit
* Python 2 (tested on 2.7) for building GN and running other build-time scripts
* [Ninja](//ninja-build.org/) for running the build command
* [Quilt](//savannah.nongnu.org/projects/quilt/) for applying patches

#### Setting up the buildspace tree

First, setup the source tree:

```
mkdir -p buildspace/downloads
./buildkit-launcher.py genbun linux_simple
./buildkit-launcher.py subdom
```

#### Generating packaging files and invoking build

**Debian package**

Builds a `deb` package for any Debian-based system

```
./buildkit-launcher.py genpkg debian --flavor minimal
# The buildspace tree can be relocated to another system for building
cd buildspace/tree
# Use dpkg-checkbuilddeps (from dpkg-dev) or mk-build-deps (from devscripts) to check for additional packages.
# If necessary, change the dependencies in debian/control to accomodate your environment.
# If necessary, modify CLANG_BASE_PATH in debian/rules to change the LLVM and Clang installation path
# (which contains files like bin/clang++, include/llvm, etc.).
dpkg-buildpackage -b -uc
```
Packages will appear in `buildspace/`

**Archive**

Builds a compressed tar archive

```
./buildkit-launcher.py genpkg linux_simple
# The buildspace tree can be relocated to another system for building
cd buildspace/tree
# Use "export CLANG_BASE_PATH=/path/to/llvm_root" to set the LLVM and Clang installation path
# (which contains files like bin/clang++, include/llvm, etc.).
# If left unset, it defaults to /usr.
./ungoogled_packaging/build.sh
./ungoogled_packaging/package.sh
```
A compressed tar archive will appear in `buildspace/`

## Advanced building information

This section holds some information about building for unsupported systems and a rough building outline.

It is recommended to have an understanding of [DESIGN.md](DESIGN.md).

**Note for unsupported systems**: There is no set procedure for building ungoogled-chromium on unsupported systems. One should already be able to build Chromium for their system before attempting to include ungoogled-chromium changes. More information about the Chromium build procedure is on [the Chromium project website](https://www.chromium.org/Home). One should also understand [DESIGN.md](DESIGN.md) before including ungoogled-chromium changes.

### Essential building requirements

Here are the essential building requirements: 

* Python 3 (tested on 3.5) for running buildkit
* Python 2 (tested on 2.7) for building GN and running other scripts
* [Ninja](//ninja-build.org/) for running the build command
* [Quilt](//savannah.nongnu.org/projects/quilt/) is recommended for patch management.
    * [python-quilt](//github.com/bjoernricks/python-quilt) can be used as well.

Alternatively, [depot_tools](//www.chromium.org/developers/how-tos/install-depot-tools) can provide Python 2 and Ninja.

### Outline building procedure

This section has a rough outline of the entire building procedure.

In the following steps, `buildkit` represents the command to invoke buildkit's CLI.

Note that each buildkit command has a help page associated with it. Pass in `-h` or `--help` for more information.

1. Create `buildspace/` and `buildspace/downloads`. Other directories are created already.
2. Generate a user config bundle from a base config bundle: `buildkit genbun base_bundle`
3. Modify the user config bundle (default location is `buildspace/user_bundle`)
4. Create the buildspace tree: `buildkit getsrc`
5. Apply domain substitution: `buildkit subdom`
6. Generate packaging files into the buildspace tree: `buildkit genpkg package_type [options]`
7. Relocate the buildspace tree (with packaging files) to the proper machine for building.
8. Invoke the packaging scripts to build and package ungoogled-chromium.
