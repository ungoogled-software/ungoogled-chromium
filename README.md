# ungoogled-chromium
**Google Chromium patches for removing Google integration, enhancing privacy, and adding features**

### Features

In addition to features provided by [Iridium Browser](https://iridiumbrowser.de/) and [Inox patchset](https://github.com/gcarq/inox-patchset), the following is also included:
* Remove additional detection of and disable specific functionality for Google hosts
* Disabled searching in Omnibox
* Disabled automatic formatting of URL in Omnibox
* Disabled JavaScript dialog boxes from showing when a page closes (onbeforeunload dialog boxes)
* Added menu item under "More tools" to clear the HTTP authentication cache on-demand
* Disabled persistent per-site settings in Preferences file
* Make all popups go to tabs
* Replaced many domains in the source code with non-existant alternatives (see `generate_domain_substitution_list.sh`)
* Stripped binaries from the source code (see `generate_cleaning_list.sh`)
* Disabled intranet redirect detector
* Debian build scripts
  * (Debian build scripts change) Move the chrome-sandbox into a separate package
* (Iridium Browser feature change) Prevent URLs with the `trk:` scheme from connecting to the Internet
* (Iridium and Inox feature change) Prevent pinging of IPv6 address when detecting the availability of IPv6

## Getting ungoogled-chromium

Users are encouraged to use [one of the available tag](https://github.com/Eloston/ungoogled-chromium/tags) versions. Binaries are available on [the releases page](https://github.com/Eloston/ungoogled-chromium/releases) for the corresponding tag.

Tags are formatted in the following manner: `{chromium_version}-{release_revision}` where

* `chromium_version` is the version of Chromium used in `x.x.x.x` format, and
* `release_revision` is an integer indicating the version of ungoogled-chromium for the corresponding Chromium version.

The `master` branch is for development, so it is not guarenteed to be in a working state.

## How ungoogled-chromium is designed

All features are implemented through patches. Patches are contained within the `patches` directory, with the exception of platform-specific patches in the `building/templates` directory

A summary of the files in the `patches` directory:
* `ungoogled-chromium/`
  * This directory contains new patches for ungoogled-chromium. They implement the features described above.
* `iridium-browser`
  * This directory contains a subset of patches from Iridium Browser.
        * Patches are not touched unless they do not apply cleanly onto the version of Chromium being built
  * Patches are from the `patchview` branch of its Git repository. [Web view of the patchview branch](https://git.iridiumbrowser.de/cgit.cgi/iridium-browser/?h=patchview)
* `inox-patchset/`
  * This directory contains a modified subset of patches from Inox patchset.
  * Patches are from [inox-patchset's GitHub](https://github.com/gcarq/inox-patchset)
  * [Inox patchset's license](https://github.com/gcarq/inox-patchset/blob/master/LICENSE)
* `debian/`
  * This directory contains patches from Debian's Chromium.
  * These patches are not Debian-specific. For those, see the `build-templates/debian/` directory
* `patch_order`
  * Determines which patches are used and what order they should be applied

## Building

[See BUILDING.md](BUILDING.md)

## Contributing

Contributers are welcome!

Use the [Issue Tracker](/Eloston/ungoogled-chromium/issues) for problems, suggestions, and questions.

You may also contribute by submitting pull requests.

## Credits

[Iridium Browser](https://iridiumbrowser.de/)

[Inox patchset](https://github.com/gcarq/inox-patchset)

[Debian for build scripts](https://tracker.debian.org/pkg/chromium-browser)

Google for Chromium

## License

GPLv3. See [LICENSE](LICENSE)
