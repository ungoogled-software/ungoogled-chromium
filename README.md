# ungoogled-chromium
**Patches for Google Chromium to remove integration with Google services and add additional features**

### Features

- Disabled background communication with Google servers
- Disabled safe browsing
- Disabled browser sign-in
- Disabled searching in Omnibox
- Disabled automatic formatting of URL in Omnibox
- Disabled JavaScript dialog boxes from showing when a page closes (onbeforeunload dialog boxes)
- Added menu item under "More tools" to clear the HTTP authentication cache on-demand
- Disabled persistent per-site settings in Preferences file
- Disabled extension autoupdating

## Patches

Patches are stored in the `patches` directory, with the exception of system-dependant patches (these are in the `build_templates` directory).

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
    dpkg-buildpackage -B -uc

Debian packages will appear under `ungoogled-chromium/`

## TODO

- Move TODO list to the Issue Tracker
- Strip binaries from source package
- Fix updating extensions via clicking "Update extensions now" (NOTE: network capture shows no attempted communication after clicking the button)
- Remove attempted communication with `www.95stat1c.qjz9zk` on startup
- Add settings menu to manually edit password database(?)
- Add Windows support

## Contributing

ungoogled-chromium is undergoing major changes for Chromium 47

Use the [Issue Tracker](/Eloston/ungoogled-chromium/issues) for problems, suggestions, and questions.

You may also contribute by submitting pull requests.

## Credits

[Iridium Browser](https://iridiumbrowser.de/)

[Inox patchset](https://github.com/gcarq/inox-patchset)

Debian for build scripts

Google for Chromium

## License

GPLv3. See [LICENSE](LICENSE)
