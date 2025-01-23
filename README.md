# ungoogled-chromium

*A lightweight approach to removing Google web service dependency*

**Help is welcome!** See the [docs/contributing.md](docs/contributing.md) document for more information.

## Objectives

In descending order of significance (i.e. most important objective first):

1. **ungoogled-chromium is Google Chromium, sans dependency on Google web services**.
2. **ungoogled-chromium retains the default Chromium experience as closely as possible**. Unlike other Chromium forks that have their own visions of a web browser, ungoogled-chromium is essentially a drop-in replacement for Chromium.
3. **ungoogled-chromium features tweaks to enhance privacy, control, and transparency**. However, almost all of these features must be manually activated or enabled. For more details, see [Feature Overview](#feature-overview).

In scenarios where the objectives conflict, the objective of higher significance should take precedence.

## Content Overview

* [Objectives](#objectives)
* [Motivation and Philosophy](#motivation-and-philosophy)
* [Feature Overview](#feature-overview)
* [**Downloads**](#downloads)
* [Source Code](#source-code)
* [**FAQ**](#faq)
* [Building Instructions](#building-instructions)
* [Design Documentation](#design-documentation)
* [**Contributing, Reporting, Contacting**](#contributing-reporting-contacting)
* [Credits](#credits)
* [Related Projects](#related-projects)
* [License](#license)

## Motivation and Philosophy

Without signing in to a Google Account, Chromium does pretty well in terms of security and privacy. However, Chromium still has some dependency on Google web services and binaries. In addition, Google designed Chromium to be easy and intuitive for users, which means they compromise on transparency and control of internal operations.

ungoogled-chromium addresses these issues in the following ways:

1. Remove all remaining background requests to any web services while building and running the browser
2. Remove all code specific to Google web services
3. Remove all uses of pre-made binaries from the source code, and replace them with user-provided alternatives when possible.
4. Disable features that inhibit control and transparency, and add or modify features that promote them (these changes will almost always require manual activation or enabling).

These features are implemented as configuration flags, patches, and custom scripts. For more details, consult the [Design Documentation](docs/design.md).

## Feature Overview

*This section overviews the features of ungoogled-chromium. For more detailed information, it is best to consult the source code.*

Contents of this section:

* [Key Features](#key-features)
* [Enhancing Features](#enhancing-features)
* [Borrowed Features](#borrowed-features)
* [Supported Platforms and Distributions](#supported-platforms-and-distributions)

### Key Features

*These are the core features introduced by ungoogled-chromium.*

* Disable functionality specific to Google domains (e.g. Google Host Detector, Google URL Tracker, Google Cloud Messaging, Google Hotwording, etc.)
    * This includes disabling [Safe Browsing](https://en.wikipedia.org/wiki/Google_Safe_Browsing). Consult [the FAQ for the rationale](https://ungoogled-software.github.io/ungoogled-chromium-wiki/faq#why-is-safe-browsing-disabled).
* Block internal requests to Google at runtime. This feature is a fail-safe measure for the above, in case Google changes or introduces new components that our patches do not disable. This feature is implemented by replacing many Google web domains in the source code with non-existent alternatives ending in `qjz9zk` (known as domain substitution; [see docs/design.md](docs/design.md#source-file-processors) for details), then [modifying Chromium to block its own requests with such domains](patches/core/ungoogled-chromium/block-trk-and-subdomains.patch). In other words, no connections are attempted to the `qjz9zk` domain.
* Strip binaries from the source code (known as binary pruning; [see docs/design.md](docs/design.md#source-file-processors) for details)

### Enhancing Features

*These are the non-essential features introduced by ungoogled-chromium.*

* Add many new command-line switches and `chrome://flags` entries to configure new features (which are disabled by default). See [docs/flags.md](docs/flags.md) for the exhaustive list.
* Add *Suggestions URL* text field in the search engine editor (`chrome://settings/searchEngines`) for customizing search engine suggestions.
* Add more URL schemes allowed to save page schemes.
* Add Omnibox search provider "No Search" to allow disabling of searching
* Add a custom cross-platform build configuration and packaging wrapper for Chromium. It currently supports many Linux distributions, macOS, and Windows. (See [docs/design.md](docs/design.md) for details on the system.)
* Force all pop-ups into tabs
* Disable automatic formatting of URLs in Omnibox (e.g. stripping `http://`, hiding certain parameters)
* Disable intranet redirect detector (extraneous DNS requests)
    * This breaks captive portal detection, but captive portals still work.
* (Iridium Browser feature change) Prevent URLs with the `trk:` scheme from connecting to the Internet
    * Also prevents any URLs with the top-level domain `qjz9zk` (as used in domain substitution) from attempting a connection.
* (Windows-specific) Do not set the Zone Identifier on downloaded files

### Borrowed Features

In addition to the features introduced by ungoogled-chromium, ungoogled-chromium selectively borrows many features from the following projects (in approximate order of significance):

* [Inox patchset](https://github.com/gcarq/inox-patchset)
* [Bromite](https://github.com/bromite/bromite)
* [Debian](https://tracker.debian.org/pkg/chromium)
* [Iridium Browser](https://iridiumbrowser.de/)

### Supported Platforms and Distributions

[See docs/platforms.md for a list of supported platforms](docs/platforms.md).

Other platforms are discussed and tracked in this repository's Issue Tracker. Learn more about using the Issue Tracker under the section [Contributing, Reporting, Contacting](#contributing-reporting-contacting).

## Downloads

### Automated or maintained builds

ungoogled-chromium is available in the following **software repositories**:

* Arch: Available in the AUR, [see instructions in ungoogled-chromium-archlinux](https://github.com/ungoogled-software/ungoogled-chromium-archlinux)
* Debian & Ubuntu: Available in OBS, find your [distribution specific instructions](https://github.com/ungoogled-software/ungoogled-chromium-debian) in the Installing section
* Fedora: Available in [COPR](https://copr.fedorainfracloud.org/coprs/) as [`wojnilowicz/ungoogled-chromium`](https://copr.fedorainfracloud.org/coprs/wojnilowicz/ungoogled-chromium/). Also available in [RPM Fusion](https://rpmfusion.org/Configuration) as `chromium-browser-privacy` (outdated).
* Gentoo: Available in [`::pf4public`](https://github.com/PF4Public/gentoo-overlay) overlay as [`ungoogled-chromium`](https://github.com/PF4Public/gentoo-overlay/tree/master/www-client/ungoogled-chromium) and [`ungoogled-chromium-bin`](https://github.com/PF4Public/gentoo-overlay/tree/master/www-client/ungoogled-chromium-bin) ebuilds
* [OpenMandriva](https://openmandriva.org/) includes ungoogled-chromium as its main browser. The `chromium` package includes all ungoogling patches.
* macOS: Available in [Homebrew](https://brew.sh/) as [`eloston-chromium`](https://formulae.brew.sh/cask/eloston-chromium). Just run `brew install --cask eloston-chromium`. Chromium will appear in your `/Applications` directory.
* FreeBSD: Available in pkg as [`www/ungoogled-chromium`](https://www.freshports.org/www/ungoogled-chromium/).

If your GNU/Linux distribution is not listed, there are distro-independent builds available via the following **package managers**:

* Flatpak: Available [in the Flathub repo](https://flathub.org/apps/details/io.github.ungoogled_software.ungoogled_chromium) as `io.github.ungoogled_software.ungoogled_chromium`
* GNU Guix: Available as `ungoogled-chromium`
* NixOS/nixpkgs: Available as `ungoogled-chromium`

### Third-party binaries

If your operating system is not listed above, you can also try to [**Download binaries from here**](https://ungoogled-software.github.io/ungoogled-chromium-binaries/)

*NOTE: These binaries are provided by anyone who are willing to build and submit them. Because these binaries are not necessarily [reproducible](https://reproducible-builds.org/), authenticity cannot be guaranteed; In other words, there is always a non-zero probability that these binaries may have been tampered with. In the unlikely event that this has happened to you, please [report it in a new issue](#contributing-reporting-contacting).*

These binaries are known as **contributor binaries**.

## Source Code

This repository only contains the common code for all platforms; it does not contain all the configuration and scripts necessary to build ungoogled-chromium. Most users will want to use platform-specific repos, where all the remaining configuration and scripts are provided for specific platforms:

[**Find the repo for a specific platform here**](docs/platforms.md).

If you wish to include ungoogled-chromium code in your own build process, consider using [the tags in this repo](https://github.com/ungoogled-software/ungoogled-chromium/tags). These tags follow the format `{chromium_version}-{revision}` where

* `chromium_version` is the version of Chromium used in `x.x.x.x` format, and
* `revision` is a number indicating the version of ungoogled-chromium for the corresponding Chromium version.

Additionally, most platform-specific repos extend their tag scheme upon this one.

**Building the source code**: [See docs/building.md](docs/building.md)

### Mirrors

List of mirrors:

* [Codeberg](https://codeberg.org): [main repo](https://codeberg.org/ungoogled-software/ungoogled-chromium) and [ungoogled-software](https://codeberg.org/ungoogled-software)

## FAQ

[See the frequently-asked questions (FAQ) on the Wiki](https://ungoogled-software.github.io/ungoogled-chromium-wiki/faq)

## Building Instructions

[See docs/building.md](docs/building.md)

## Design Documentation

[See docs/design.md](docs/design.md)

## Contributing, Reporting, Contacting

* For reporting and contacting, see [SUPPORT.md](SUPPORT.md)
* If you're willing to help, check out the [Issue Tracker](https://github.com/ungoogled-software/ungoogled-chromium/issues) and especially issues, which [need help](https://github.com/ungoogled-software/ungoogled-chromium/issues?q=is%3Aopen+is%3Aissue+label%3A%22help+wanted%22)
* For contributing (e.g. how to help, submitting changes, criteria for new features), see [docs/contributing.md](docs/contributing.md)
* If you have some small contributions that don't fit our criteria, consider adding them to [ungoogled-software/contrib](https://github.com/ungoogled-software/contrib) or [our Wiki](https://github.com/ungoogled-software/ungoogled-chromium-wiki) instead.

## Credits

* [The Chromium Project](https://www.chromium.org/)
* [Inox patchset](https://github.com/gcarq/inox-patchset)
* [Debian](https://tracker.debian.org/pkg/chromium-browser)
* [Bromite](https://github.com/bromite/bromite)
* [Iridium Browser](https://iridiumbrowser.de/)
* The users for testing and debugging, [contributing code](https://github.com/ungoogled-software/ungoogled-chromium/graphs/contributors), providing feedback, or simply using ungoogled-chromium in some capacity.

## Related Projects

List of known projects that fork or use changes from ungoogled-chromium:

* [Bromite](https://github.com/bromite/bromite) (Borrows some patches. Features builds for Android)
* [ppc64le fork](https://github.com/leo-lb/ungoogled-chromium) (Fork with changes to build for ppc64le CPUs)

## License

BSD-3-clause. See [LICENSE](LICENSE)
