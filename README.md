# ungoogled-chromium
**Patches for Google Chromium to remove integration with Google services and add additional features**

### Features

In addition to features provided by [Iridium Browser](https://iridiumbrowser.de/) and [Inox patchset](https://github.com/gcarq/inox-patchset), the following is also included:
* Remove additional detection of Google hosts
* Disabled searching in Omnibox
* Disabled automatic formatting of URL in Omnibox
* Disabled JavaScript dialog boxes from showing when a page closes (onbeforeunload dialog boxes)
* Added menu item under "More tools" to clear the HTTP authentication cache on-demand
* Disabled persistent per-site settings in Preferences file
* Make all popups go to tabs
* Replaced many domains in the source code with non-existant alternatives (see `domain_patcher.sh`)
* Stripped binaries from the source code (see `source_cleaner.sh`)
* Debian build scripts
  * (Debian build scripts change) Move the chrome-sandbox into a separate package
* (Iridium Browser feature change) Prevent URLs with the `trk:` scheme from connecting to the Internet
* (Iridium and Inox feature change) Prevent pinging of IPv6 address when detecting the availability of IPv6

## Patches

All features come in the form of patches. Patches are stored in the `patches` directory, with the exception of platform-specific patches (which are in the `build_templates` directory).

Currently, the patches are applied on top of Chromium 48.0.2564.116. See the Building section below for information on using these patches.

Here's an overview of the files in the `patches` directory:
* `ungoogled-chromium/`
  * This directory contains new patches for ungoogled-chromium. They implement the features described above.
* `iridium-browser`
  * This directory contains patches derived from Iridium Browser.
  * Patches are from the `patchview` branch of its Git repository. [Web view of the patchview branch](https://git.iridiumbrowser.de/cgit.cgi/iridium-browser/?h=patchview)
* `inox-patchset/`
  * This directory contains patches derived from Inox patchset.
  * Patches are from [inox-patchset's GitHub](https://github.com/gcarq/inox-patchset)
  * [Inox patchset's license](https://github.com/gcarq/inox-patchset/blob/master/LICENSE)
* `debian/`
  * This directory contains patches from Debian's Chromium.
  * These patches are not Debian-specific. For those, see the `build-templates/debian/` directory
* `patch_order`
  * Determines which patches are used and what order they should be applied

## Releases

[Builds with these patches are available here](https://github.com/Eloston/ungoogled-chromium/releases).

## Building

ungoogled-chromium provides scripts to automate the downloading, patching, and building of Chromium with these patches. Here's an overview of the building scripts and files:
* `build-sandbox` - This directory is the build sandbox; the container for all files used and generated during building. It is created when the building environment is setup.
* `build_templates` - This holds the system-dependant files that are used for compiling and generating a binary package. They are copied into the build sandbox by the build setup scripts.
  * `debian` - This contains files to generate a dpkg debian directory. Debian-specific patches are located here.
  * `ubuntu` - This contains files to generate a dpkg debian directory for Ubuntu
* `download_source.sh` - This script downloads the source tarball from `commondatastorage.googleapis.com` and unpacks it into the build sandbox.
  * It accepts arguments; pass in `-h` for more information.
* `domain_patcher.sh` - This script replaces multiple domain name strings with invalid domain names.
  * It recursively works down the current working directory, and thus should be run at the root of the build sandbox.
* `source_cleaner.sh` - This script strips the source tree of mostly all binary files.
  * It should be run at the root of the build sandbox.
* `generate_debian_scripts.sh` - This script creates a dpkg debian directory in the build sandbox for Debian
* `generate_ubuntu_scripts.sh` - This script creates a dpkg debian directory in the build sandbox for Ubuntu
* `build_debian.sh` - This is the main build script for Debian and derivative distributions. It handles the downloading, patching, and building of .deb packages.
  * This script will invoke the other scripts to do certain tasks.
  * It accepts arguments; pass in `-h` for more information.
  * Currently, only Debian Stretch 64-bit and Ubuntu Wily 64-bit are tested.

### Debian and derivatives
**NOTE:** Instructions are tested on Debian Jessie 64-bit and Stretch 64-bit, and Ubuntu Wily 64-bit

**Debian Jessie users**: ungoogled-chromium is configured to build against the system's [FFmpeg](https://www.ffmpeg.org/) (available in Stretch and onwards); [Libav](http://libav.org) (used in Jessie) will not work. However, FFmpeg is available in `jessie-backports`. To install it, add `jessie-backports` to the apt sources, and then install `libavutil-dev`, `libavcodec-dev`, and `libavformat-dev` from it. Note that this will replace Libav.

Run these steps on the system you want to build packages for.

    git clone https://github.com/Eloston/ungoogled-chromium.git
    cd ungoogled-chromium
    # Run dpkg-checkbuilddeps to find packages needed for building
    ./build_debian.sh -A

Debian packages will appear under `ungoogled-chromium/`

Pass the `-h` flag into `build_debian.sh` or `download_source.sh` for more options.

### Arch Linux

For Arch Linux, consider using [Inox patchset](https://github.com/gcarq/inox-patchset); one of the projects which ungoogled-chromium draws its patches from. It offers pre-built binaries and is also available in AUR.

### Other systems, platforms, and configurations

Consult the build instructions on the [Chromium homepage](http://www.chromium.org/Home) to learn how to build Chromium for your system.

The patches in the `patches` directory should work for any build of Chromium. They assume a clean Chromium source tree processed by `domain_patcher.sh`.

These patches are also tested with the GYP flags defined in [`build_templates/debian/rules`](build_templates/debian/rules). Note that enabling some flags, such as `safe_browsing`, may cause the build to fail.

Note about `domain_patcher.sh`: This script will break URLs in the source tree pointing to Google servers. If your building steps requires additional downloads (such as the the PNaCl toolkit), note that scripts in the source tree may fail to work.

## Contributing

Contributers are welcome!

Use the [Issue Tracker](/Eloston/ungoogled-chromium/issues) for problems, suggestions, and questions.

You may also contribute by submitting pull requests.

## Credits

[Iridium Browser](https://iridiumbrowser.de/)

[Inox patchset](https://github.com/gcarq/inox-patchset)

Debian for build scripts

Google for Chromium

## License

GPLv3. See [LICENSE](LICENSE)
