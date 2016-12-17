# Building ungoogled-chromium

**Notice for master branch users**: The information in this document may not apply to the latest tag version. Please consult the documentation from the tag instead.

## General building requirements

The following is needed to fully use `buildlib`:
* Python 3 (tested on 3.5) for running `buildlib`
* The following can be provided by [Google's depot_tools](//www.chromium.org/developers/how-tos/install-depot-tools) (but it is recommended to obtain these from their respective websites)
    * Python 2 (tested on 2.7) for building GN and running other scripts
    * [Ninja](//ninja-build.org/) for running the build command

There are additional requirements for specific platforms. See the following sections for more information.

## How to build

Building is done by simply invoking `build.py`. It will take care of the setup and building processes.

Currently, there is no command-line-configurable build script. You must create a script or modify `build.py` to use `buildlib`.

See the following for more information.

## Debian and derivatives

As of now, Debian Stretch 64-bit and Ubuntu Xenial 64-bit are tested.
This may work on other Debian-based distributions and 32-bit systems

### Additional Requirements

**Note for Debian Jessie users**: ungoogled-chromium is configured to build against the system's [FFmpeg](//www.ffmpeg.org/) (available in Stretch and onwards); [Libav](//libav.org) (used in Jessie) will not work. However, FFmpeg is available in `jessie-backports`. To install it, add `jessie-backports` to the apt sources, and then install `libavutil-dev`, `libavcodec-dev`, and `libavformat-dev` from it. Note that this will replace Libav.

Make sure to install the `quilt` and `build-essential` packages first, otherwise `buildlib` will not work properly.

### Build

Run these steps on the system you want to build packages for:

    # Change directory to ungoogled-chromium's root directory
    ./build.py # This will check system packages and print out additional packages to install

Debian packages will appear in the current working directory.

## Windows

Google only supports [Windows 7 x64 or newer](https://chromium.googlesource.com/chromium/src/+/51.0.2704.106/docs/windows_build_instructions.md#Setting-up-the-environment-for-Visual-Studio). These instructions are tested on Windows 10 Home x64.

For maximum portability, the build configuration will generate x86 binaries by default. This can be changed to x64 by setting `builder.target_cpu = CPUArch.x64` in `build.py`.

### Additional Requirements
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

### Setting up the build environment

Make sure all of the following are in the `PATH`:
* Python 2 as `python`
* Ninja as `ninja`
* GNU patch as `patch`
* gperf as `gperf`
* bison as `bison`

See `build.py` for more on customizing the build environment or process.

### Build

    # Change directory to ungoogled-chromium's root directory
    path\to\python3 build.py

## macOS

**NOTE: There is no official maintainer for this platform. If there is a problem, please submit a pull request or issue**

Tested on macOS 10.11.6

Credits to [9Morello](//github.com/9Morello) for most of the work done on this platform.

### Additional Requirements

* Xcode 7
* Homebrew
* Perl (for creating a `.dmg` package)

### Setting up the build environment

1. Install Quilt via Homebrew: `brew install quilt`
2. Install Ninja via Homebrew: `brew install ninja`

See `build.py` for more on customizing the build environment or process.

### Build

    # Change directory to ungoogled-chromium's root directory
    python3 build.py

## Arch Linux

**This is a WIP**

For now, see the instructions for Other Linux distributions. The resulting binary will still use system libraries.

## Other Linux distributions (semi-statically-linked builds)

### Setting up the build environment

* Install the following through your package manager or elsewhere:
    * `clang`, preferrably the latest version
    * Python 3.5 or newer (or 3.4 if necessary)
    * Python 2
    * `quilt`
    * `ninja`
* Follow [these instructions](//chromium.googlesource.com/chromium/src/+/55.0.2883.75/docs/linux_build_instructions.md#Install-additional-build-dependencies) to install additional dependencies for building

### Build

    # Change directory to ungoogled-chromium's root directory
    python3 build.py

## Other systems, platforms, and configurations

Please read the section in the README explaning ungoogled-chromium's design first.

For other Linux distributions, consider using `LinuxStaticBuilder` in `buildlib.linux`.

Consult the build instructions on the [Chromium homepage](//www.chromium.org/Home) for platform-specific building information.

You can use `depot_tools` to setup the Chromium source tree in `build/sandbox` if `buildlib`'s source downloading system does not work on a platform. However, please note that this will involve executing Google binaries part of `depot_tools` and will run scripts that can download and run more Google binaries.

The main set of patches (in `resources/common/patches`) should work on most, if not all, platforms supported by desktop Chromium. Some patches are there to fix building with certain build flags, so those may not work with other platforms or configurations. However, the patches as they are should apply as long as there is a clean and unmodified source tree.

It is not recommended to run domain substitution or source cleaning, especially if your build requires additional downloads from Google.

The domain substitution list, source cleaning list, and some patches in `resources/common` are designed to work with the build flags defined. They may require modifications if the flags are changed.
