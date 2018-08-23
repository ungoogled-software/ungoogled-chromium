# Building ungoogled-chromium

This document contains building instructions for supported platforms and configurations.

For configurations, you may try augmenting the standard Chromium build procedure with tools from ungoogled-chromium; please read [design.md](design.md) for more details.

## IMPORTANT - Please read this section first

**Statuses of platform support**: Because platform support varies across stable versions, [this Wiki page tracks platform support for the current stable](//github.com/Eloston/ungoogled-chromium/wiki/statuses). *Please check the status before attempting a build or posting an issue*.

**Choosing a version**: *It is highly recommended to choose a tag version for building.* `master` and other branches are not guarenteed to be in a working state.

## Contents

* [Debian and its derivatives](#debian-and-its-derivatives)
* [Windows](#windows)
* [macOS](#macos)
* [Arch Linux](#arch-linux)
* [OpenSUSE](#opensuse)
* [Any Linux distribution](#any-linux-distribution)

## Debian and its derivatives


These instructions will create `.deb` packages. It uses ungoogled-chromium's variation of Debian's `debian` directory.

The build should work on the CPU architectures `amd64`, `i386`, `arm64`, and `armhf`.

The final size of the sandbox with build artifacts is over 5 GB. On systems with enough RAM, it can be built entirely within `tmpfs` without swap memory.

### Setting up the build environment

Install base requirements: `# apt install packaging-dev python3 ninja-build`

On Debian 9 (stretch), `stretch-backports` APT source is used to obtain LLVM 6.0. Do NOT use debhelper 11 from backports, as it will be incompatible with other dpkg tools.

### Building locally

```sh
mkdir -p build/src
./get_package.py PACKAGE_TYPE_HERE build/src/debian
cd build/src
# Use dpkg-checkbuilddeps (from dpkg-dev) or mk-build-deps (from devscripts) to check for additional packages.
# If necessary, change the dependencies in debian/control to accomodate your environment.
# If necessary, modify AR, NM, CC, and CXX variables in debian/rules
debian/rules setup-local-src
dpkg-buildpackage -b -uc
```

where `PACKAGE_TYPE_HERE` is one of the following:

* `debian_stretch` for Debian 9 (stretch)
* `debian_buster` for Debian 10 (buster)
* `ubuntu_bionic` for Ubuntu 18.04 (bionic)
* `debian_minimal` for any other Debian-based system that isn't based on one of the above versions.

Packages will appear under `build/`.

### Building via source package

```sh
mkdir -p build/src
./get_package.py PACKAGE_TYPE_HERE build/src/debian
cd build/src
# If necessary, change the dependencies in debian/control to accomodate your environment.
# If necessary, modify AR, NM, CC, and CXX variables in debian/rules
debian/rules get-orig-source
cd ..
dpkg-source -b src
```

(`PACKAGE_TYPE_HERE` is the same as above)

Source package files should appear in `build/`

## Windows

Google only supports [Windows 7 x64 or newer](https://chromium.googlesource.com/chromium/src/+/64.0.3282.168/docs/windows_build_instructions.md#system-requirements). These instructions are tested on Windows 10 Home x64.

NOTE: The default configuration will build 64-bit binaries for maximum security (TODO: Link some explanation). This can be changed to 32-bit by changing `target_cpu` to `"x32"` (*with* quotes) in the user config bundle GN flags config file (default path is `buildspace/user_bundle/gn_flags.map`

### Setting up the build environment

#### Setting up Visual Studio

[Follow the official Windows build instructions](https://chromium.googlesource.com/chromium/src/+/64.0.3282.168/docs/windows_build_instructions.md#visual-studio).

**IMPORTANT**: According to [a Chromium developer in Google Groups](https://groups.google.com/a/chromium.org/d/msg/chromium-dev/PsqFiJ-j5B4/9wO3wflWCQAJ), due to bugs in the 10.0.16299.15 SDK (that comes with Visual Studio 2017 as of Feburary 2018) *will not work* to build Chromium. The 10.0.15063 SDK must be downloaded and installed. This can be downloaded from the [Windows SDK Archive](https://developer.microsoft.com/en-us/windows/downloads/sdk-archive).

When installing the SDK, the "Debugging Tools for Windows" feature must be enabled. Visual Studio 2017 does not enable this by default, so it has to be added in by selecting "Modify" on the SDK entry in "Add or remove programs".

#### Other build requirements

**IMPORTANT**: Currently, the `MAX_PATH` path length restriction (which is 260 characters by default) must be lifted in order for buildkit to function properly. One such setup that works is Windows 10 (which added this option since Anniversary) with Python 3.6 or newer from the official installer (which contains the manifest files that allow use of long file paths). Other possible setups are being discussed in [Issue #345](https://github.com/Eloston/ungoogled-chromium/issues/345).

1. Setup the following:

    * 7-zip
    * Python 2.7 for scripts in Chromium, with pypiwin32 module (`pip install pypiwin32`)
    * Python 3.5+ for buildkit

2. Make sure Python 2.7 is accessible in `PATH` as `python`.

### Setting up the buildspace tree and packaging files

Setting up via CMD:

```
mkdir buildspace\downloads
py buildkit-launcher.py genbun windows
py buildkit-launcher.py getsrc
py buildkit-launcher.py subdom
py buildkit-launcher.py genpkg windows
```

The buildspace tree can be relocated to another system for building if necessary.

### Invoking build

1. In a CMD instance, apply patches:

    ```
    py buildspace\tree\ungoogled_packaging\scripts\apply_patch_series.py
    ```

2. Run build script: `buildspace\tree\ungoogled_packaging\build.bat`
3. Run packaging script: `buildspace\tree\ungoogled_packaging\package.bat`
    * A zip archive will be created in `buildspace\tree\ungoogled_packaging\`

## macOS

Tested on macOS 10.11-10.13

### Additional Requirements

* Xcode 7-9
* Homebrew
* Perl (for creating a `.dmg` package)

### Setting up the build environment

1. Install Ninja via Homebrew: `brew install ninja`
2. Install GNU coreutils (for `greadlink` in packaging script): `brew install coreutils`

### Building

```sh
mkdir -p build/src/ungoogled_packaging
./get_package.py macos build/src/ungoogled_packaging
cd build/src
./ungoogled_packaging/build.sh
```

A `.dmg` should appear in `build/`

## Arch Linux

A PKGBUILD is used to build on Arch Linux. It handles downloading, unpacking, building, and packaging.

Requirements: Python 3 is needed to generate the PKGBUILD. The PKGBUILD contains build dependency information.

Generate the PKGBUILD:

```
./get_package.py archlinux ./
```

A PKGBUILD will be generated in the current directory. It is a standalone file that can be relocated as necessary.

## openSUSE

Tested on openSUSE Leap 42.3

### Setting up the build environment

Install the following packages : `# sudo zypper install perl-Switch dirac-devel hunspell-devel imlib2-devel libdc1394 libdc1394-devel libavcodec-devel yasm-devel libexif-devel libtheora-devel schroedinger-devel minizip-devel python-beautifulsoup4 python-simplejson libvdpau-devel slang-devel libjack-devel libavformat-devel SDL-devel ninja binutils-gold bison cups-devel desktop-file-utils fdupes flex gperf hicolor-icon-theme libcap-devel libelf-devel libgcrypt-devel libgsm libgsm-devel libjpeg-devel libpng-devel libva-devel ncurses-devel pam-devel pkgconfig re2-devel snappy-devel update-desktop-files util-linux wdiff alsa Mesa-dri-devel cairo-devel libavutil-devel libavfilter-devel libdrm2 libdrm-devel libwebp-devel libxslt-devel libopus-devel rpm-build` 

**Note**: There may be additional package requirements besides those listed above, if so they will be listed when using `rpmbuild` to create the ungoogled-chromium package. 

Follow the following guide to set up Python 3.6.4: [https://gist.github.com/antivanov/01ed4eac2d7486a170be598b5a0a4ac7](https://gist.github.com/antivanov/01ed4eac2d7486a170be598b5a0a4ac7) 

As of Chromium 66.0.3359.117, llvm, lld and clang version 6 or greater is required to avoid compiler errors.

### Generate packaging scripts

Before executing the following commands, make sure you are using python 3.6 as was mentioned in the build environment section of this guide.

```sh
mkdir -p build/{download_cache,src}
# TODO: The download commands should be moved into the packaging scripts
./get_package.py opensuse build/src/ungoogled_packaging
```

Before proceeding to the build chromium, open a new tab or otherwise exit the python 3.6 virtual environment, as it will cause errors in the next steps.

### Setting up environment for RPM build

Note: This section only has to be performed once.

Execute the following commands:

```sh
mkdir -p ~/rpm/{BUILD,RPMS,SOURCES,SPECS,SRPMS}

cat <<EOF >~/.rpmmacros
%HOME       %{expand:%%(cd; pwd)}
%_topdir    %{HOME}/rpm
EOF
```

### Invoking build and installing package

```sh
cd build/src
./ungoogled_packaging/setup.sh
cd ~/rpm
rpmbuild -v -bb --clean SPECS/ungoogled-chromium.spec
```

The RPM will be located in `~/rpm/RPMS/{arch}/` once rpmbuild has finished. It can be installed with the command `sudo rpm -i {path to RPM}`

## Any Linux distribution

These instructions will build packages compatible with any Linux distribution that Chromium supports. Unlike distro-specific packages, they are portable and have minimal dependencies with system libraries (just as in regular Chromium).

### Requirements

TODO: Document all libraries and tools needed to build. For now, see the build dependencies for Debian systems.

* Python 3 (tested on 3.5) for buildkit
* Python 2 (tested on 2.7) for building GN and running other build-time scripts
* [Ninja](//ninja-build.org/) for running the build command
* LLVM 6.0 (including Clang and LLD)

For Debian-based systems, these can be installed via apt: `# apt install clang-6.0 lld-6.0 llvm-6.0-dev python python3 ninja-build`

* Some systems, like Debian 9 (stretch), need their backports repo enabled.

### Build a tar archive

```sh
mkdir -p build/src
./get_package.py linux_simple build/src/ungoogled_packaging
cd build/src
# Use "export ..." for AR, NM, CC, CXX, or others to specify the compiler to use
# It defaults to LLVM tools. See ./ungoogled_packaging/build.sh for more details
./ungoogled_packaging/build.sh
./ungoogled_packaging/package.sh
```

A compressed tar archive will appear in `build/src/ungoogled_packaging/`

### Building an AppImage, Flatpak, or Snap package

TODO. See [Issue #36](//github.com/Eloston/ungoogled-chromium/issues/36)
