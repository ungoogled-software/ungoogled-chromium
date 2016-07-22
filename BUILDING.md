# Building ungoogled-chromium

**Notice for master branch users**: The information in this document may not apply to the latest tag version. Please consult the documentation from the tag instead.

## The building system

ungoogled-chromium provides a flexible and extensible Python library called [`buildlib`](buildlib) that does source code downloading, source cleaning, domain substitution, patching, building, and packaging. There's no documentation on `buildlib` yet, but it's pretty straight-forward to use. [See `build.py`](build.py) for an example on using `buildlib`.

Currently, there is no command-line-configurable build script. You must create a script to use `buildlib`.

## General building requirements

The following is needed to fully use `buildlib`:
* Python 3 (tested on 3.5) for running `buildlib`
* The below can be provided by [Google's depot_tools](https://www.chromium.org/developers/how-tos/install-depot-tools)
    * Python 2 (tested on 2.7) for running gyp
    * [Jinja2](http://jinja.pocoo.org/) for running gyp
    * [Ninja](https://ninja-build.org/) for running the build command

There are additional requirements for specific platforms. See the following sections for more information.

## How to build

Building is done by simply invoking a Python script like `build.py`. It will take care of the setup and building processes. See the following for more information.

## Debian and derivatives

As of now, only Debian Stretch 64-bit is tested. Ubuntu Xenial 64-bit support will come soon.
This may work on other Debian-based distributions and 32-bit systems

**Note for Debian Jessie users**: ungoogled-chromium is configured to build against the system's [FFmpeg](https://www.ffmpeg.org/) (available in Stretch and onwards); [Libav](http://libav.org) (used in Jessie) will not work. However, FFmpeg is available in `jessie-backports`. To install it, add `jessie-backports` to the apt sources, and then install `libavutil-dev`, `libavcodec-dev`, and `libavformat-dev` from it. Note that this will replace Libav.

Run these steps on the system you want to build packages for.

    git clone https://github.com/Eloston/ungoogled-chromium.git
    cd ungoogled-chromium
    git checkout $(git describe --tags `git rev-list --tags --max-count=1`) # Checkout newest tag
    dpkg-checkbuilddeps resources/debian/dpkg_dir/control # Use this to see the packages needed to build
    ./build.py

Debian packages will appear in the current working directory.

## Arch Linux

For Arch Linux, consider using [Inox patchset](https://github.com/gcarq/inox-patchset); one of the projects which ungoogled-chromium draws its patches from. It offers pre-built binaries and is also available in AUR.

## Windows

TODO. See Issue #1

## Other systems, platforms, and configurations

Consult the build instructions on the [Chromium homepage](http://www.chromium.org/Home) to build Chromium for your system.

The main set of patches (in `resources/common/patches`) should work on most, if not all, platforms supported by desktop Chromium. Some patches are there to fix building with certain build flags, so those may not work with other platforms or configurations. However, the patches as they are should apply as long as there is a clean and unmodified source tree.

It is not recommended to run domain substitution or source cleaning, especially if your build requires additional downloads from Google.

The domain substitution list, source cleaning list, and some patches in `resources/common` are designed to work with the build flags defined. They may require modifications if the flags are changed.
