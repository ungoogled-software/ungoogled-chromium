# ungoogled-chromium

*Bringing back the "Don't" in "Don't be evil"*

**ungoogled-chromium is Google Chromium**, sans integration with Google. It also features some tweaks to enhance privacy, control, and transparency *(almost all of which require manual activation or enabling)*.

**ungoogled-chromium retains the default Chromium experience as closely as possible**. Unlike other Chromium forks that have their own visions of a web browser, ungoogled-chromium is essentially a drop-in replacement for Chromium.

**Help is always welcome!** See the [docs/contributing.md](docs/contributing.md) document for more information.

## Content Overview

* [Motivation and Philosophy](#motivation-and-philosophy)
* [Feature Overview](#feature-overview)
* [**Downloads**](#downloads)
    * [Software Repositories](#software-repositories)
    * [Contributor Binaries](#contributor-binaries)
    * [Source Code](#source-code)
* [**FAQ**](#faq)
* [Building Instructions](#building-instructions)
* [Design Documentation](#design-documentation)
* [**Contributing, Reporting, Contacting**](#contributing-reporting-contacting)
* [Credits](#credits)
* [License](#license)

## Motivation and Philosophy

A number of features or background services communicate with Google servers despite the absence of an associated Google account or compiled-in Google API keys. Furthermore, the normal build process for Chromium involves running Google's own high-level commands that invoke many scripts and utilities, some of which download and use pre-built binaries provided by Google. Even the final build output includes some pre-built binaries. Fortunately, the source code is available for everything.

From a technical standpoint, ungoogled-chromium is a set of configuration flags, patches, and custom scripts. These components altogether strive to accomplish the following:

* Disable or remove offending services and features that communicate with Google or weaken privacy
* Strip binaries from the source tree, and use those provided by the system or build them from source
* Disable features that inhibit control and transparency, and add or modify features that promote them (these changes will almost always require manual activation or enabling).

Since these goals and requirements are not precise, unclear situations are discussed and decided on a case-by-case basis.

## Feature Overview

*This section overviews the features of ungoogled-chromium. For more detailed information, it is best to consult the source code.*

Contents of this section:

* [Key Features](#key-features)
* [Enhancing Features](#enhancing-features)
* [Borrowed Features](#borrowed-features)
* [Supported Platforms and Distributions](#supported-platforms-and-distributions)

### Key Features

*These are the core features introduced by ungoogled-chromium.*

* Replace many web domains in the source code with non-existent alternatives ending in `qjz9zk` (known as domain substitution; [see docs/design.md](docs/design.md#source-file-processors) for details)
* Strip binaries from the source code (known as binary pruning; [see docs/design.md](docs/design.md#source-file-processors) for details)
* Disable functionality specific to Google domains (e.g. Google Host Detector, Google URL Tracker, Google Cloud Messaging, Google Hotwording, etc.)
    * This includes disabling [Safe Browsing](//en.wikipedia.org/wiki/Google_Safe_Browsing). Consult [the FAQ for the rationale](//ungoogled-software.github.io/ungoogled-chromium-wiki/faq#why-is-safe-browsing-disabled).
* Add many new command-line switches and `chrome://flags` entries to configure disabled-by-default features. See [docs/flags.md](docs/flags.md) for the exhaustive list.

### Enhancing Features

*These are the non-essential features introduced by ungoogled-chromium.*

* Use HTTPS by default when a URL scheme is not provided (e.g. Omnibox, bookmarks, command-line)
* Add *Suggestions URL* text field in the search engine editor (`chrome://settings/searchEngines`) for customizing search engine suggestions.
* Add menu item under "More tools" to clear the HTTP authentication cache on-demand
* Add more URL schemes allowed to save page schemes.
* Add Omnibox search provider "No Search" to allow disabling of searching
* Add a custom cross-platform build configuration and packaging wrapper for Chromium. It currently supports many Linux distributions, macOS, and Windows. (See [docs/design.md](docs/design.md) for details on the system.)
* Force all pop-ups into tabs
* Disable automatic formatting of URLs in Omnibox (e.g. stripping `http://`, hiding certain parameters)
* Disable intranet redirect detector (extraneous DNS requests)
    * This breaks captive portal detection, but captive portals still work.
* (Iridium Browser feature change) Prevent URLs with the `trk:` scheme from connecting to the Internet
    * Also prevents any URLs with the top-level domain `qjz9zk` (as used in domain substitution) from attempting a connection.
* (Iridium and Inox feature change) Prevent pinging of IPv6 address when detecting the availability of IPv6. See the `--set-ipv6-probe-false` flag above to adjust the behavior instead.
* (Windows-specific) Do not set the Zone Identifier on downloaded files

### Borrowed Features

In addition to the features introduced by ungoogled-chromium, ungoogled-chromium selectively borrows many features from the following projects (in approximate order of significance):

* [Inox patchset](//github.com/gcarq/inox-patchset)
* [Bromite](//github.com/bromite/bromite)
* [Debian](//tracker.debian.org/pkg/chromium-browser)
* [Iridium Browser](//iridiumbrowser.de/)

### Supported Platforms and Distributions

Currently, only desktop platforms are supported. Functionality of specific desktop platforms may vary across different releases. For more details, see [Statuses in the Wiki](//ungoogled-software.github.io/ungoogled-chromium-wiki/statuses).

Other platforms are discussed and tracked in GitHub's Issue Tracker. Learn more about using the Issue Tracker under the section [Contributing, Reporting, Contacting](#contributing-reporting-contacting).

## Downloads

*To download and run ungoogled-chromium:*

* Download from [Software Repositories](#software-repositories) if your system is supported.
* Otherwise, download [Contributor Binaries](#contributor-binaries).

To build ungoogled-chromium, see [Source Code](#source-code).

### Software Repositories

*Install and run ungoogled-chromium from a software repository:*

* Arch Linux: [Available in AUR as `ungoogled-chromium`](https://aur.archlinux.org/packages/ungoogled-chromium/)
    * NOTE: `ungoogled-chromium-bin` is *not* officially part of ungoogled-chromium. Please submit all issues to the maintainer of the PKGBUILD.
* Gentoo Linux: [`::chaoslab`](https://gitlab.com/chaoslab/chaoslab-overlay) overlay maintains an *unofficial*  [`ungoogled-chromium`](https://gitlab.com/chaoslab/chaoslab-overlay/tree/master/www-client/ungoogled-chromium) ebuild.
* GNU Guix: Available as `ungoogled-chromium`.
* macOS cask: Available as `eloston-chromium`

### Contributor Binaries

*Download, install, and run ungoogled-chromium from machine code provided by volunteers.*

**IMPORTANT**: These binaries are provided by anyone who are willing to build and submit them. Because these binaries are not necessarily [reproducible](https://reproducible-builds.org/), authenticity cannot be guaranteed; In other words, there is always a non-zero probability that these binaries may have been tampered with. In the unlikely event that this has happened to you, please [report it in a new issue](#contributing-reporting-contacting).

[**Download from the contributor binaries website**](//ungoogled-software.github.io/ungoogled-chromium-binaries/)

The release versioning scheme follows that of the tags. Please see [Getting the source code](#getting-the-source-code) section for more details.

**To contribute binaries**, [consult the instructions in the ungoogled-chromium-binaries repository](//github.com/ungoogled-software/ungoogled-chromium-binaries)

### Source Code

**Picking the version to download**: You are encouraged to download [one of the tags](//github.com/Eloston/ungoogled-chromium/tags). The latest tag may not be the applicable for all platforms. To determine the tag to use, please see the [Status page in the Wiki](https://ungoogled-software.github.io/ungoogled-chromium-wiki/statuses). Tags are versioned in the following format: `{chromium_version}-{release_revision}` where

* `chromium_version` is the version of Chromium used in `x.x.x.x` format, and
* `release_revision` is a number indicating the version of ungoogled-chromium for the corresponding Chromium version.

Not all tags are stable for all platforms. See the [Statuses in the Wiki](//ungoogled-software.github.io/ungoogled-chromium-wiki/statuses) to determine the tag to use.

**Building the source code**: [See docs/building.md](docs/building.md)

## FAQ

[See the frequently-asked questions (FAQ) on the Wiki](//ungoogled-software.github.io/ungoogled-chromium-wiki/faq)

## Building Instructions

[See docs/building.md](docs/building.md)

## Design Documentation

[See docs/design.md](docs/design.md)

## Contributing, Reporting, Contacting

* For reporting and contacting, see [SUPPORT.md](SUPPORT.md)
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
