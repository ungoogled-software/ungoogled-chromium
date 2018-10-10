# ungoogled-chromium

*Bringing back the "Don't" in "Don't be evil"*

**ungoogled-chromium is Google Chromium**, sans integration with Google. It also features some tweaks to enhance privacy, control, and transparency *(almost all of which require manual activation or enabling)*.

**ungoogled-chromium retains the default Chromium experience as closely as possible**. Unlike other Chromium forks that have their own visions of a web browser, ungoogled-chromium is essentially a drop-in replacement for Chromium.

## Motivation and Description

A number of features or background services communicate with Google servers despite the absence of an associated Google account or compiled-in Google API keys. Furthermore, the normal build process for Chromium involves running Google's own high-level commands that invoke many scripts and utilities, some of which download and use pre-built binaries provided by Google. Even the final build output includes some pre-built binaries. Fortunately, the source code is available for everything.

From a technical standpoint, ungoogled-chromium is a set of configuration flags, patches, and custom scripts. These components altogether strive to accomplish the following:

* Disable or remove offending services and features that communicate with Google or weaken privacy
* Strip binaries from the source tree, and use those provided by the system or build them from source
* Disable features that inhibit control and transparency, and add or modify features that promote them (these changes will almost always require manual activation or enabling).

Since these goals and requirements are not precise, unclear situations are discussed and decided on a case-by-case basis.

**ungoogled-chromium always welcomes more help!** See the [docs/contributing.md](docs/contributing.md) document for more information.

## Table of Contents

* [Features](#features)
    * [Supported platforms and distributions](#supported-platforms-and-distributions)
* [**Download pre-built packages**](#download-pre-built-packages)
* [Getting the source code](#getting-the-source-code)
* [**FAQ**](#faq)
* [Design and implementation](#design-and-implementation)
* [Building](#building)
* [**Contributing, Reporting, Contacting**](#contributing-reporting-contacting)
* [Credits](#credits)
* [License](#license)

## Features

A number of ungoogled-chromium's changes are subtle and evolve over time. As a result, it is best to consult the source code for complete and up-to-date information.

ungoogled-chromium selectively borrows many of its features from the following (in no particular order):
* [Debian](//tracker.debian.org/pkg/chromium-browser)
* [Inox patchset](//github.com/gcarq/inox-patchset)
* [Iridium Browser](//iridiumbrowser.de/)
* [Bromite](//github.com/bromite/bromite)

Most of the **additional** features are as follows:
* Replace many web domains in the source code with non-existent alternatives ending in `qjz9zk` (known as domain substitution; [see docs/design.md](docs/design.md#source-file-processors))
* Strip binaries from the source code (known as binary pruning; [see docs/design.md](docs/design.md#source-file-processors))
* Disable functionality specific to Google domains (e.g. Google Host Detector, Google URL Tracker, Google Cloud Messaging, Google Hotwording, etc.)
* Add Omnibox search provider "No Search" to allow disabling of searching
* Disable automatic formatting of URLs in Omnibox (e.g. stripping `http://`, hiding certain parameters)
* Added menu item under "More tools" to clear the HTTP authentication cache on-demand
* Add new command-line switches and `chrome://flags` entries:
    * `--disable-beforeunload` - (Not in `chrome://flags`) Disables JavaScript dialog boxes triggered by `beforeunload`
    * `--disable-search-engine-collection` - Disable automatic search engine scraping from webpages.
    * `--enable-stacked-tab-strip` and `--enable-tab-adjust-layout` - These flags adjust the tab strip behavior. `--enable-stacked-tab-strip` is also configurable in `chrome://flags` Please note that they are not well tested, so proceed with caution.
    * `--extension-mime-request-handling` - Change how extension MIME types (CRX and user scripts) are handled. Acceptable values are `download-as-regular-file` or `install-always`. Leave unset to use normal behavior. It is also configurable under `chrome://flags`
    * `--fingerprinting-canvas-measuretext-noise` (Added flag to Bromite feature) - Scale the output values of Canvas::measureText() with a randomly selected factor in the range -0.0003% to 0.0003%, which are recomputed on every document initialization.
    * `--fingerprinting-client-rects-noise` (Added flag to Bromite feature) - Implements fingerprinting deception of JS APIs `getClientRects()` and `getBoundingClientRect()` by scaling their output values with a random factor in the range -0.0003% to 0.0003%, which are recomputed for every document instantiation.
    * `--fingerprinting-canvas-image-data-noise` (Added flag to Bromite feature) - Implements fingerprinting deception for Canvas image data retrieved via JS APIs. In the data, at most 10 pixels are slightly modified.
    * `--max-connections-per-host` (from Bromite) - Configure the maximum allowed connections per host.
    * `--set-ipv6-probe-false` - (Not in `chrome://flags`) Forces the result of the browser's IPv6 probing (i.e. IPv6 connectivity test) to be unsuccessful. This causes IPv4 addresses to be prioritized over IPv6 addresses. Without this flag, the probing result is set to be successful, which causes IPv6 to be used over IPv4 when possible.
* Force all pop-ups into tabs
* Disable [Safe Browsing](//en.wikipedia.org/wiki/Google_Safe_Browsing)
    * See the [FAQ](//ungoogled-software.github.io/ungoogled-chromium-wiki/faq#why-is-safe-browsing-disabled)
* Disable intranet redirect detector (extraneous DNS requests)
    * This breaks captive portal detection, but captive portals still work.
* Add more URL schemes allowed for saving
* (Iridium Browser feature change) Prevent URLs with the `trk:` scheme from connecting to the Internet
    * Also prevents any URLs with the top-level domain `qjz9zk` (as used in domain substitution) from attempting a connection.
* (Iridium and Inox feature change) Prevent pinging of IPv6 address when detecting the availability of IPv6. See the `--set-ipv6-probe-false` flag above to adjust the behavior instead.
* Support for building Linux packages for multiple distributions (work in progress)
* Windows support
    * Does not set the Zone Identifier on downloaded files

**NOTE: Although it is the top priority to eliminate bugs and privacy-invading code, there will be those that slip by due to the fast-paced growth and evolution of the Chromium project.**

### Supported platforms and distributions

Currently, only desktop platforms are supported. Functionality of specific desktop platforms may vary across different releases. For more details, see [Statuses in the Wiki](//ungoogled-software.github.io/ungoogled-chromium-wiki/statuses).

Other platforms are discussed and tracked in GitHub's Issue Tracker. Learn more about using the Issue Tracker under the section [Contributing, Reporting, Contacting](#contributing-reporting-contacting).

## Download pre-built packages

### Contributor binaries

**IMPORTANT**: These binaries are provided by anyone who are willing to build and submit them. Because these binaries are not necessarily [reproducible](https://reproducible-builds.org/), authenticity cannot be guaranteed.

[**Visit the contributor binaries website for download links**](//ungoogled-software.github.io/ungoogled-chromium-binaries/)

[Website source code and contribution instructions](//github.com/ungoogled-software/ungoogled-chromium-binaries)

The release versioning scheme follows that of the tags. Please see [Getting the source code](#getting-the-source-code) section for more details.

### Alternative installation methods

Arch Linux: [Available in AUR as `ungoogled-chromium`](https://aur.archlinux.org/packages/ungoogled-chromium/)

* **NOTE**: `ungoogled-chromium-bin` is *not* officially part of ungoogled-chromium. Please submit all issues to the maintainer of the PKGBUILD.

macOS cask: Available as `eloston-chromium`

## Getting the source code

Users are encouraged to use [one of the tags](//github.com/Eloston/ungoogled-chromium/tags). The latest tag may not be the applicable for all platforms. To determine the tag to use, please see the [Status page in the Wiki](https://ungoogled-software.github.io/ungoogled-chromium-wiki/statuses).

Tags are versioned in the following format: `{chromium_version}-{release_revision}` where

* `chromium_version` is the version of Chromium used in `x.x.x.x` format, and
* `release_revision` is a number indicating the version of ungoogled-chromium for the corresponding Chromium version.

Not all tags are stable for all platforms. See the [Statuses in the Wiki](//ungoogled-software.github.io/ungoogled-chromium-wiki/statuses) to determine the tag to use.

## FAQ

[See the frequently-asked questions (FAQ) on the Wiki](//ungoogled-software.github.io/ungoogled-chromium-wiki/faq)

## Design and implementation

[See docs/design.md](docs/design.md)

## Building

[See docs/building.md](docs/building.md)

## Contributing, Reporting, Contacting

* For reporting and contating, see [SUPPORT.md](SUPPORT.md)
* For contributing (e.g. how to help, submitting changes, criteria for new features), see [docs/contributing.md](docs/contributing.md)

## Credits

* [The Chromium Project](//www.chromium.org/)
* [Inox patchset](//github.com/gcarq/inox-patchset)
* [Debian](//tracker.debian.org/pkg/chromium-browser)
* [Bromite](//github.com/bromite/bromite)
* [Iridium Browser](//iridiumbrowser.de/)
* The users for testing and debugging, [contributing code](//github.com/Eloston/ungoogled-chromium/graphs/contributors), providing feedback, or simply using ungoogled-chromium in some capacity.

## License

BSD-3-clause. See [LICENSE](LICENSE)
