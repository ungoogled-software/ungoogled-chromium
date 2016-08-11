# Building ungoogled-chromium

**Notice for master branch users**: The information in this document may not apply to the latest tag version. Please consult the documentation from the tag instead.

## The building system

ungoogled-chromium provides a flexible and extensible Python library called [`buildlib`](buildlib) that does source code downloading, source cleaning, domain substitution, patching, building, and packaging. There's no documentation on `buildlib` yet, but it's pretty straight-forward to use. See `build_*.py` for examples on using `buildlib`.

Currently, there is no command-line-configurable build script. You must create a script to use `buildlib`.

## General building requirements

The following is needed to fully use `buildlib`:
* Python 3 (tested on 3.5) for running `buildlib`
* The below can be provided by [Google's depot_tools](//www.chromium.org/developers/how-tos/install-depot-tools)
    * Python 2 (tested on 2.7) for running gyp
    * [Ninja](//ninja-build.org/) for running the build command

There are additional requirements for specific platforms. See the following sections for more information.

## How to build

Building is done by simply invoking a Python script like `build.py`. It will take care of the setup and building processes. See the following for more information.

## Debian and derivatives

As of now, Debian Stretch 64-bit and Ubuntu Xenial 64-bit are tested.
This may work on other Debian-based distributions and 32-bit systems

**Note for Debian Jessie users**: ungoogled-chromium is configured to build against the system's [FFmpeg](//www.ffmpeg.org/) (available in Stretch and onwards); [Libav](//libav.org) (used in Jessie) will not work. However, FFmpeg is available in `jessie-backports`. To install it, add `jessie-backports` to the apt sources, and then install `libavutil-dev`, `libavcodec-dev`, and `libavformat-dev` from it. Note that this will replace Libav.

Run these steps on the system you want to build packages for:

    # Change directory to ungoogled-chromium's root directory
    dpkg-checkbuilddeps resources/debian/dpkg_dir/control # Use this to see the packages needed to build. This includes packages for "General building requirements"
    ./build_debian.py

Debian packages will appear in the current working directory.

## Arch Linux

For Arch Linux, consider using [Inox patchset](//github.com/gcarq/inox-patchset); one of the projects which ungoogled-chromium draws its patches from. It offers pre-built binaries and is also available in AUR.

## Windows

Google only supports [Windows 7 x64 or newer](https://chromium.googlesource.com/chromium/src/+/51.0.2704.106/docs/windows_build_instructions.md#Setting-up-the-environment-for-Visual-Studio). These instructions are tested on Windows 10 Home x64.

For maximum portability, the build configuration will generate x86 binaries.

In addition to the general building requirements, there are additional requirements:
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
    * Get the Binaries, Developer files, and Dependencies

Make sure all of the following are in the `PATH`:
* Python 2 as `python`
* Ninja as `ninja`
* GNU patch as `patch`
* gperf as `gperf`
* bison as `bison`

Also, ensure that `TEMP` and `TMP` environment variables point to existing directories.

See `build_windows.py` for more on customizing the build environment or process.

Build steps:

    # Change directory to ungoogled-chromium's root directory
    path\to\python3 build_windows.py

## Other systems, platforms, and configurations

Please read the section in the README explaning ungoogled-chromium's design first.

Consult the build instructions on the [Chromium homepage](//www.chromium.org/Home) for platform-specific building information.

The main set of patches (in `resources/common/patches`) should work on most, if not all, platforms supported by desktop Chromium. Some patches are there to fix building with certain build flags, so those may not work with other platforms or configurations. However, the patches as they are should apply as long as there is a clean and unmodified source tree.

It is not recommended to run domain substitution or source cleaning, especially if your build requires additional downloads from Google.

The domain substitution list, source cleaning list, and some patches in `resources/common` are designed to work with the build flags defined. They may require modifications if the flags are changed.
