# ungoogled-chromium

**Modifications to Google Chromium for removing Google integration and enhancing privacy, control, and transparency**

## Motivation and Description

A number of features or background services communicate with Google servers despite the absence of an associated Google account or compiled-in Google API keys. Furthermore, the normal build process for Chromium involves running Google's own high-level commands that invoke many scripts and utilities, some of which download and use pre-built binaries provided by Google. Even the final build output includes some pre-built binaries. Fortunately, the source code is available for everything.

ungoogled-chromium is a set of configuration flags, patches, and custom scripts. These components altogether strive to accomplish the following:
* Disable or remove offending services and features that communicate with Google or weaken privacy
* Strip binaries from the source tree, and use those provided by the system or build them from source
* Add, modify, or disable features that inhibit control and transparency (these changes are minor and do not have significant impacts on the general user experience)

**ungoogled-chromium should not be considered a fork of Chromium**. The main reason for this is that a fork is associated with more significant deviations from the Chromium, such as branding, configuration formats, file locations, and other interface changes. ungoogled-chromium will not modify the Chromium browser outside of the project's goals.

Since these goals and requirements are not precise, unclear situations are discussed and decided on a case-by-case basis.

**ungoogled-chromium is looking for contributors**. See the [Contributing, Reporting, Contacting](#contributing-reporting-contacting) section for more information.

## Table of Contents

* [Features](#features)
    * [Supported platforms and distributions](#supported-platforms-and-distributions)
* [Download pre-built packages](#download-pre-built-packages)
* [Getting the source code](#getting-the-source-code)
* [Frequently-asked questions](#frequently-asked-questions)
* [Design and implementation](#design-and-implementation)
* [Building](#building)
* [Contributing, Reporting, Contacting](#contributing-reporting-contacting)
    * [Pull request guidelines](#pull-request-guidelines)
* [Credits](#credits)
* [License](#license)

## Features

A number of ungoogled-chromium's changes are subtle and evolve over time. As a result, it is best to consult the source code for complete and up-to-date information.

ungoogled-chromium selectively borrows many of its features from the following:
* [Debian](//tracker.debian.org/pkg/chromium-browser)
* [Inox patchset](//github.com/gcarq/inox-patchset)
* [Iridium Browser](//iridiumbrowser.de/)

Most of the **additional** features are as follows:
* Replace many web domains in the source code with non-existent alternatives ending in `qjz9zk` (known as domain substitution)
* Strip binaries from the source code (known as source cleaning)
    * This includes all pre-built executables, shared libraries, and other forms of machine code. They are substituted with system or user-provided equivalents, or built from source.
    * However a few data files are left in as they do not contain machine code and are needed for building.
* Disable functionality specific to Google domains (e.g. Google Host Detector, Google URL Tracker, Google Cloud Messaging, Google Hotwording, etc.)
* Add Omnibox search provider "No Search" to allow disabling of searching
* Disable automatic formatting of URLs in Omnibox (e.g. stripping `http://`, hiding certain parameters)
* Added menu item under "More tools" to clear the HTTP authentication cache on-demand
* Add new command-line switches and `chrome://flags` entries:
    * `--extension-mime-request-handling` - Change how extension MIME types (CRX and user scripts) are handled. Acceptable values are `download-as-regular-file` or `install-always`. Leave unset to use normal behavior. It is also configurable under `chrome://flags`
    * `--enable-stacked-tab-strip` and `--enable-tab-adjust-layout` - These flags adjust the tab strip behavior. `--enable-stacked-tab-strip` is also configurable in `chrome://flags` Please note that they are not well tested, so proceed with caution.
* Force all pop-ups into tabs
* Disable [Safe Browsing](//en.wikipedia.org/wiki/Google_Safe_Browsing)
    * See the [FAQ](FAQ.md#why-is-safe-browsing-disabled)
* Disable intranet redirect detector (extraneous DNS requests)
    * This breaks captive portal detection, but captive portals still work.
* Add more URL schemes allowed for saving
* (Iridium Browser feature change) Prevent URLs with the `trk:` scheme from connecting to the Internet
    * Also prevents any URLs with the top-level domain `qjz9zk` (as used in domain substitution) from attempting a connection.
* (Iridium and Inox feature change) Prevent pinging of IPv6 address when detecting the availability of IPv6
* Support for building Linux packages for multiple distributions (work in progress)
* Windows support
    * Does not set the Zone Identifier on downloaded files

**NOTE: Although it is the top priority to eliminate bugs and privacy-invading code, there will be those that slip by due to the fast-paced growth and evolution of the Chromium project.**

### Supported platforms and distributions

Currently, only desktop platforms are supported. Functionality of specific desktop platforms may vary across different releases. For more details, see [Statuses in the Wiki](//github.com/Eloston/ungoogled-chromium/wiki/statuses).

Other platforms are discussed and tracked in GitHub's Issue Tracker. Learn more about using the Issue Tracker under the section [Contributing, Reporting, Contacting](#contributing-reporting-contacting).

## Download pre-built packages

### Contributor binaries

These binaries are provided by anyone who are willing to build and submit them. Because these binaries are not reproducible, their functionality cannot be guaranteed.

[All downloads](//ungoogled-software.github.io/ungoogled-chromium-binaries/)

* [Page source code and contribution instructions](//github.com/ungoogled-software/ungoogled-chromium-binaries)

The release versioning scheme follows that of the tags. See the next section for more details.

### Alternative installation methods

macOS cask: Available as `eloston-chromium`

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

## Contributing, Reporting, Contacting

Contributions are welcome!

The [Issue Tracker](//github.com/Eloston/ungoogled-chromium/issues) is the main area for development activity. It tracks problems, suggestions, and questions. Issues marked with the `help wanted` tag are changes that needs discussion or assistance.

There is also a [Gitter chat room](https://gitter.im/ungoogled-software/Lobby) for real-time discussion.

For pull requests, please read the guidelines below first.

### Pull request guidelines

* Minor changes, such as bug fixes, documentation fixes, or small feature additions, will generally not need prior approval.
* More significant changes should be proposed through an issue first, where it can be discussed publically and then approved.
* When in doubt, create an issue first.

## Credits

[Iridium Browser](//iridiumbrowser.de/)

[Inox patchset](//github.com/gcarq/inox-patchset)

[Debian](//tracker.debian.org/pkg/chromium-browser)

[The Chromium Project](//www.chromium.org/)

## License

BSD-3-clause. See [LICENSE](LICENSE)
