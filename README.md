# ungoogled-chromium

**A Google Chromium variant for removing Google integration and enhancing privacy, control, and transparency**

A number of features or background services communicate with Google servers despite the absence of an associated Google account or compiled-in Google API keys. Furthermore, the normal build process for Chromium involves running Google's own high-level commands that invoke many scripts and utilities, some of which download and use pre-built binaries provided by Google. Even the final build output includes some pre-built binaries. Fortunately, the source code is available for everything.

ungoogled-chromium is a set of configuration flags, patches, and custom scripts. These components altogether strive to accomplish the following:
* Disable or remove offending services and features that communicate with Google or weaken privacy
* Strip binaries from the source tree, and use those provided by the system or build them from source
* Add, modify, or disable features that inhibit control and transparency (these changes are minor and do not have significant impacts on the general user experience)

**ungoogled-chromium is looking for contributers**. See the [Contributing](#contributing) section for more information.

Table of Contents
* [Features](#features)
    * [Supported platforms and distributions](#supported-platforms-and-distributions)
* [Download pre-built packages](#download-pre-built-packages)
* [Getting the source code](#getting-the-source-code)
* [Frequently-asked questions](#frequently-asked-questions)
* [Design and implementation](#design-and-implementation)
* [Building](#building)
* [Contributing](#contributing)
    * [Pull requests](#pull-requests)
* [Credits](#credits)
* [License](#license)

## Features

In addition to features from [Debian](//tracker.debian.org/pkg/chromium-browser), [Inox patchset](//github.com/gcarq/inox-patchset), and [Iridium Browser](//iridiumbrowser.de/):
* Replace many web domains in the source code with non-existent alternatives ending in `qjz9zk` (known as domain substitution)
* Strip binaries from the source code (known as source cleaning)
    * This includes all pre-built executables, shared libraries, and other forms of machine code. They are substituted with system or user-provided equivalents, or built from source.
    * However some data files (e.g. `icudtl.dat` for Unicode and Globalization support and `*_page_model.bin` that define page models for the DOM Distiller) are left in as they do not contain machine code and are needed for building.
* Disable functionality specific to Google domains (e.g. Google Host Detector, Google URL Tracker, Google Cloud Messaging, Google Hotwording, etc.)
* Add Omnibox search provider "No Search" to allow disabling of searching
* Disable automatic formatting of URLs in Omnibox (e.g. stripping `http://`, hiding certain parameters)
* Disable JavaScript dialog boxes from showing when a page closes (onbeforeunload events)
    * Bypasses the annoying dialog boxes that spawn when a page is being closed
* Added menu item under "More tools" to clear the HTTP authentication cache on-demand
* Force all pop-ups into tabs
* Disable [Safe Browsing](//en.wikipedia.org/wiki/Google_Safe_Browsing)
    * See the [FAQ](FAQ.md#why-is-safe-browsing-disabled)
* Disable WebRTC
    * This will be configurable in the future.
* Disable intranet redirect detector
    * Prevents unnecessary invalid DNS requests to the DNS server.
    * This breaks captive portal detection, but captive portals still work.
* Add more URL schemes allowed for saving
    * Note that this generally works only for the MHTML option, since an MHTML page is generated from the rendered page and not the original cached page like the HTML option.
* (Iridium Browser feature change) Prevent URLs with the `trk:` scheme from connecting to the Internet
    * Also prevents any URLs with the top-level domain `qjz9zk` (as used in domain substitution) from attempting a connection.
* (Iridium and Inox feature change) Prevent pinging of IPv6 address when detecting the availability of IPv6
* Support for building Debian and Ubuntu packages
    * Creates a separate package `chrome-sandbox` for the SUID sandbox
        * Not necessary to install if the kernel option `unprivileged_userns_clone` is enabled
* Windows support with these changes:
    * Build `wow_helper.exe` from source instead of using the pre-built version
    * Build `swapimport.exe` from source instead of downloading it from Google (requires [customized syzygy source code](//github.com/Eloston/syzygy))
    * Build `yasm.exe` from source instead of using the pre-built version
    * Use user-provided building utilities instead of the ones bundled with Chromium (currently `gperf` and `bison`)
    * Do not set the Zone Identifier on downloaded files (which is a hassle to unset)

**DISCLAIMER: Although it is the top priority to eliminate bugs and privacy-invading code, there will be those that slip by due to the fast-paced growth and evolution of the Chromium project.**

### Supported platforms and distributions
* Debian
* Ubuntu
* Windows
* Mac OS

## Download pre-built packages

[Downloads for the latest release](//github.com/Eloston/ungoogled-chromium/releases/latest)

[List of all releases](//github.com/Eloston/ungoogled-chromium/releases)

The release versioning scheme follows that of the tags. See the next section for more details.

## Getting the source code

Users are encouraged to use [one of the tags](//github.com/Eloston/ungoogled-chromium/tags). The `master` branch is not guaranteed to be in a working state.

Tags are versioned in the following format: `{chromium_version}-{release_revision}` where

* `chromium_version` is the version of Chromium used in `x.x.x.x` format, and
* `release_revision` is a number indicating the version of ungoogled-chromium for the corresponding Chromium version.

## Frequently-asked questions

[See FAQ.md](FAQ.md)

## Design and implementation

[See DESIGN.md](DESIGN.md)

## Building

[See BUILDING.md](BUILDING.md)

## Contributing

Contributers are welcome!

**Update as of September 2016**: I, Eloston, am in a period of time where I do not have as much time as I had before to work on this project. If you are interested in making a change, I encourage you to submit a pull request. Please read the Pull requests section below for submission guidelines.
* Additionally, issues marked with the `help wanted` tag are changes I need others to help with. Please read the issue's comment thread for more details on what needs to be done.

Use the [Issue Tracker](//github.com/Eloston/ungoogled-chromium/issues) for problems, suggestions, and questions.

### Pull requests

Pull requests are also welcome. Here are some guidelines:
* Changes that fix certain configurations or add small features and do not break compatibility are generally okay
* Larger changes, such as those that change `buildlib`, should be proposed through an issue first before submitting a pull request.
* When in doubt, propose the idea through an issue first.

## Credits

[Iridium Browser](//iridiumbrowser.de/)

[Inox patchset](//github.com/gcarq/inox-patchset)

[Debian](//tracker.debian.org/pkg/chromium-browser)

[The Chromium Project](//www.chromium.org/)

## License

GPLv3. See [LICENSE](LICENSE)
