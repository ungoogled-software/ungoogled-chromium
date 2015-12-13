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

All features come in the form of patches. Patches are stored in the `patches` directory, with the exception of system-dependant patches (these are in the `build_templates` directory).

Here's some information on what's in the `patches` directory:
* `ungoogled-chromium/`
  * This directory contains new patches for ungoogled-chromium
* `iridium-browser`
  * This directory contains patches from Iridium Browser.
  * Patches are from the `patchview` branch of its Git repository. [Web view of the patchview branch](https://git.iridiumbrowser.de/cgit.cgi/iridium-browser/?h=patchview)
* `inox-patchset/`
  * This directory contains patches from Inox patchset.
  * Patches are from [inox-patchset's GitHub](https://github.com/gcarq/inox-patchset)
  * [Inox patchset's license](https://github.com/gcarq/inox-patchset/blob/master/LICENSE)
* `debian/`
  * This directory contains patches from Debian's Chromium.
  * These patches are not Debian-specific. For those, see the `build-templates/debian/` directory
* `patch_order`
  * Determines which patches are used and what order they should be applied

## Building

Right now, only Debian build scripts are provided.

### Debian and derivatives
**NOTE:** Tested on Debian Stretch 64-bit

    git clone https://github.com/Eloston/ungoogled-chromium.git
    cd ungoogled-chromium
    # Run dpkg-checkbuilddeps to find packages needed for building
    ./generate_debian.sh
    cd build-sandbox
    ./debian/rules download-source
    ../source_cleaner.sh
    ../domain_patcher.sh
    dpkg-buildpackage -b -uc

Debian packages will appear under `ungoogled-chromium/`

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
