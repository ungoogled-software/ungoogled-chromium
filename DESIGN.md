# Design

This document contains a high-level technical description of ungoogled-chromium and its components.

## Overview

ungoogled-chromium consists of the following major components:

* [Configuration](#configuration)
    * Configuration [files](#configuration-files) and [bundles](#configuration-bundles)
    * [Source file processors](#source-file-processors)
    * [Patches](#patches)
* [Packaging](#packaging)
* [buildkit](#buildkit)
* [Buildspace](#buildspace)

The following sections describe each component.

## Configuration

Configuration is a broad term that referes to patches, build flags, and metadata about Chromium source code. It consists of the following components:

* Configuration [files](#configuration-files) and [bundles](#configuration-bundles)
* [Source file processors](#source-file-processors)
* [Patches](#patches)

The following sections describe each component in more depth.

### Configuration Files

Configuration files (or config files) are files that store build configuration and source code changes for a build. The kinds of config files are:

* Compiler, linker and metaprocessor (e.g. GN, ninja) flags
* Chromium code metadata
* Patches to apply

**IMPORTANT**: For consistency, all config files must be encoded in UTF-8.

All config file names have an extension that determines their type. The extensions are:

* `.list` - A list of strings delimited by a carriage return character.
* `.map` - A mapping of string keys and values, with entries delimited by a carriage return, and keys and values delimited by an equal (`=`) sign.
* `.ini` - An INI-like config format (specifically, the implementation by Python's `configparser`)

Config files are usually stored in a [configuration bundle](#configuration-bundles) or in some form in the `resources` directory of the repository.

### Configuration Bundles

*Also known as config bundles, or bundles.*

Configuration bundles are a collection of config files grouped by system, platform, or target. They are stored as filesystem directories containing the config files. There are two kinds of config bundles:

* *Base bundles* - Bundles included in ungoogled-chromium (which reside under `resources/config_bundles`). They are generally used for creating user bundles. All base bundles must include `basebundlemeta.ini`. Unlike user bundles, the patches used by a base bundle are stored in `resources/patches`

    Many configurations share a lot in common. To reduce duplication, base bundles can depend on other base bundles by specifying a list of dependencies in `basebundlemeta.ini`. When dependencies are present, base bundles only contain the config file data that is modified in or added to its dependencies.
    * Base bundles may depend on mixins. Mixins are like base bundles, but they are only used as dependencies for base bundles or other mixins, and their names are always prefixed with `_mixin`. This means that mixins are not valid configurations; they only contain partial data. These are similar in idea to mixins in Python.
    * Base bundle dependency relationships must be representable by a [polytree](https://en.wikipedia.org/wiki/Polytree) to be valid.

    Base bundle pieces combine different types of files in the following manner (file types are explained in [the Configuration Files section](#configuration-files)):
    * TODO
* *User bundles* - Bundles intended for use in building. They cannot have dependencies, so they must contain all configuration data. They are usually generated from base bundles, from which they can be modified by the user. Unlike base bundles, all patches used must be contained within the user bundle.

Config bundles can only contain the following files:

* `cleaning.list` - [See the Source File Processors section](#source-file-processors)
* `domain_regex.list` - [See the Source File Processors section](#source-file-processors)
* `domain_substitution.list` - [See the Source File Processors section](#source-file-processors)
* `extra_deps.ini` - Extra archives to download and unpack into the buildspace tree. This includes code not bundled in the Chromium source code archive that is specific to a non-Linux platform. On platforms such as macOS, this also includes a pre-built LLVM toolchain for covenience (which can be removed and built from source if necessary).
* `gn_flags.map` - GN arguments to set before building.
* `patch_order.list` - The series of patches to apply with paths relative to the `patches/` directory (whether they be in `resources/` or the bundle itself).
* `version.ini` - Tracks the the Chromium version to use, the ungoogled-chromium revision, and any configuration-specific version information.
* `basebundlemeta.ini` *(Base config bundles only)* - See the description of base bundles above.
* `patches/` *(User config bundles only)* - Contains the patches referenced by `patch_order.list`. [See the Patches section](#patches) for more details.

### Source File Processors

Source file processors are utilities that directly manipulate the Chromium source tree before building. Currently, there are two such utilities: source cleaning, and domain substitution.

**Source Cleaning**: Strips binaries from the source code. This includes pre-built executables, shared libraries, and other forms of machine code. Most are substituted with system or user-provided equivalents, or are built from source; those binaries that cannot be removed do not contain machine code.

The list of files to remove are determined by the config file `source_cleaning.list`. This config file is generated by `developer_utilities/update_lists.py`.

**Domain Substitution**: Replaces Google and several other web domain names in the Chromium source code with non-existant alternatives ending in `qjz9zk`. With a few patches from ungoogled-chromium, any requests with these domain names sent via `net::URLRequest` in the Chromium code are blocked and notify the user via a info bar. These changes are mainly used as a backup measure to to detect potentially unpatched requests to Google.

Similar to source cleaning, the list of files to modify are listed in `domain_substitution.list`; it is also updated with `developer_utilities/update_lists.py`.

The regular expressions to use are listed in `domain_regex.list`; the search and replacement expressions are delimited with a pound (`#`) symbol. The restrictions for the entries are as follows:
* All replacement expressions must end in the TLD `qjz9zk`.
* The search and replacement expressions must have a one-to-one correspondance: no two search expressions can match the same string, and no two replacement expressions can result in the same string.

### Patches

All of ungoogled-chromium's patches for the Chromium source code are located in `resources/patches`. The patches in this directory are referenced by base config bundles' `patch_order.list` config file. When a user config bundle is created, only the patches required by the user bundle's `patch_order.list` config file are copied from `resources/patches` into the user bundle's `patches/` directory.

A file with the extension `.patch` is patch using the [unified format](https://en.wikipedia.org/wiki/Diff_utility#Unified_format). The requirements and recommendations for patch files are as follows:
    * All paths in the hunk headers must begin after the first slash (which corresponds to the argument `-p1` for GNU patch).
    * All patches must apply cleanly (i.e. no fuzz).
    * It is recommended that hunk paths have the `a/` and `b/` prefixes, and a context of 3 (like the git default).
    * All patches must be encoded in UTF-8 (i.e. same encoding as config files).

Patches are grouped into the following directories:

* `debian/` - Patches from Debian's Chromium
    * Patches are not modified unless they conflict with Inox's patches
    * These patches are not Debian-specific. For those, see the `resources/debian/patches` directory
* `inox-patchset/` - Contains a modified subset of patches from Inox patchset.
    * Some patches such as those that change branding are omitted
    * Patches are not modified unless they do not apply cleanly onto the version of Chromium being built
    * Patches are from [inox-patchset's GitHub](//github.com/gcarq/inox-patchset)
    * [Inox patchset's license](//github.com/gcarq/inox-patchset/blob/master/LICENSE)
* `iridium-browser/` - Contains a modified subset of patches from Iridium Browser.
    * Some patches such as those that change branding or URLs to point to Iridium's own servers are omitted
    * Patches are not modified unless they conflict with Debian's or Inox's patches
    * Patches are from the `patchview` branch of Iridium's Git repository. [Git webview of the patchview branch](//git.iridiumbrowser.de/cgit.cgi/iridium-browser/?h=patchview)
* `opensuse/` - Patches from openSUSE's Chromium
* `ubuntu/` -  Patches from Ubuntu's Chromium
* `ungoogled-chromium/` - Patches by ungoogled-chromium developers
    * `macos/` - Patches specific to macOS
    * `windows/` - Patches specific to Windows

## Packaging

Packaging is the process of producing a distributable package for end-users. This entails building the source code and packaging the build outputs.

**IMPORTANT**: Packaging and configuration are distinct concepts. The names used in each are meaningful only within their respective contexts. However, there may be some implicit minor coupling between packaging types and configuration bundles due to the nature of their purposes and implementation.

There are different kinds of packaging types; each has differing package outputs and invocation requirements. Some packaging types divide the building and package generation steps; some have it all-in-one. The current packaging types are as follows:

* `debian` - Builds Debian `.deb.` packages for Debian and derivative systems.
* `linux_simple` - Builds a compressed tar archive for Linux.
* `macos` - Builds a `.dmg` for macOS.

The directories in `resources/packaging` correspond to the packaging type names. The only exception is `shared`, which is reserved for files shared among multiple packaging types.

## buildkit

buildkit is a Python 3 library and CLI application for building ungoogled-chromium. Its main purpose is to setup the buildspace tree and any requested building or packaging scripts from the `resources/` directory.

Use `buildkit-launcher.py` to invoke the buildkit CLI. Pass in `-h` or `--help` for usage details.

For examples of using buildkit, see [BUILDING.md](BUILDING.md).

## Buildspace

Buildspace is a directory that contains all intermediate and final files for building. Its default location is in the repository directory as `buildspace/`. The directory structure is as follows:

* `tree` - The Chromium source tree, which also contains build intermediates.
* `downloads` - Directory containing all files download; this is currently the Chromium source code archive and any potential extra dependencies.
* `user_bundle` - The user config bundle used for building.
* Packaged build artifacts

    (The directory may contain additional files if developer utilities are used)
