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

* `.list` (list config file) - A list of strings delimited by a carriage return character.
* `.map` (mapping config file) - A mapping of string keys and values, with entries delimited by a carriage return, and keys and values delimited by an equal (`=`) sign.
* `.ini` (ini config file) - An INI-like config format (specifically, the implementation by Python's `configparser`)

Config files are usually stored in a [configuration bundle](#configuration-bundles) or in some form in the `resources` directory of the repository.

### Configuration Bundles

*Also known as config bundles, or bundles.*

Configuration bundles are a collection of config files grouped by system, platform, or target. They are stored as filesystem directories containing the config files.

Many configurations share a lot in common. To reduce duplication, bundles can depend on other bundles by specifying a list of dependencies in the `depends` key of `bundlemeta.ini`. When dependencies are present, bundles only contain the config file data that is modified in or added to its dependencies. The following are additional points about bundle dependencies:
* Direct dependencies for any one bundle are ordered; the ordering specifies how dependency configuration is resolved in a consistent manner.
* This ordering is determined by the order in which they appear in the `depends` key of `bundlemeta.ini`; dependencies are applied from right to left just like multiple inheritance in Python.
* The graph of all bundle dependency relationships must be representable by a [polytree](https://en.wikipedia.org/wiki/Polytree) to be valid.
* Due to the direct dependency ordering and polytree requirements, all dependencies for a bundle can be resolved to a consistent sequence. This sequence is known as the *dependency order*.
* Bundles may depend on mixins. Mixins are like bundles, but they are only used as dependencies for bundles or other mixins, and their names are always prefixed with `_mixin`. This means that mixins are not valid configurations; they only contain partial data. These are similar in idea to mixins in Python.

Bundles merge config file types from its dependencies in the following manner (config file types are explained in [the Configuration Files section](#configuration-files)):
* `.list` - List files are joined in the dependency order.
* `.map` - Entries (key-value pairs) are collected together. If a key exists in two or more dependencies, the subsequent dependencies in the dependency order have precedence.
* `.ini` - Sections are collected together. If a section exists in two or more dependencies, its keys are resolved in an identical manner as mapping config files.

Bundles vary in specificity; some apply across multiple kinds of systems, and some apply to a specific family. However, no bundle may become more specific than a "public" system variant; since there is no concrete definition, the policy for Linux distribution bundles is used to illustrate:
* Each family of Linux distributions should have their own bundle (e.g. Debian, Fedora)
* Each distribution within that family can have their own bundle ONLY if they cannot be combined (e.g. Debian and Ubuntu)
* Each version for a distribution can have their own bundle ONLY if the versions in question cannot be combined and should be supported simultaneously (e.g. Debian testing and stable, Ubuntu LTS and regular stables)
* Custom Linux systems for personal or limited use **should not** have a bundle.

Among the multiple bundles and mixins, here are a few noteworthy ones:
* `common` - The bundle used by all other bundles. It contains most, if not all, of the feature-implementing configuration.
* `linux_rooted` - The bundle used by Linux bundles that build against system libraries.
* `linux_portable` - The bundle used for building with minimal dependency on system libraries. It is more versatile than `linux_rooted` since it is less likely to break due to system library incompatibility.

Config bundles can only contain the following files:

* `bundlemeta.ini` - Metadata for the bundle.
* `pruning.list` - [See the Source File Processors section](#source-file-processors)
* `domain_regex.list` - [See the Source File Processors section](#source-file-processors)
* `domain_substitution.list` - [See the Source File Processors section](#source-file-processors)
* `downloads.ini` - Archives to download and unpack into the buildspace tree. This includes code not bundled in the Chromium source code archive that is specific to a non-Linux platform. On platforms such as macOS, this also includes a pre-built LLVM toolchain for covenience (which can be removed and built from source if desired).
* `gn_flags.map` - GN arguments to set before building.
* `patch_order.list` - The series of patches to apply with paths relative to the `patches/` directory.

### Source File Processors

Source file processors are utilities that directly manipulate the Chromium source tree before building. Currently, there are two such utilities: binary pruning, and domain substitution.

**Binary Pruning**: Strips binaries from the source code. This includes pre-built executables, shared libraries, and other forms of machine code. Most are substituted with system or user-provided equivalents, or are built from source; those binaries that cannot be removed do not contain machine code.

The list of files to remove are determined by the config file `pruning.list`. This config file is generated by `developer_utilities/update_lists.py`.

**Domain Substitution**: Replaces Google and several other web domain names in the Chromium source code with non-existant alternatives ending in `qjz9zk`. These changes are mainly used as a backup measure to to detect potentially unpatched requests to Google. Note that domain substitution is a crude process, and *may not be easily undone*.

With a few patches from ungoogled-chromium, any requests with these domain names sent via `net::URLRequest` in the Chromium code are blocked and notify the user via a info bar. 

Similar to binary pruning, the list of files to modify are listed in `domain_substitution.list`; it is also updated with `developer_utilities/update_lists.py`.

The regular expressions to use are listed in `domain_regex.list`; the search and replacement expressions are delimited with a pound (`#`) symbol. The restrictions for the entries are as follows:
* All replacement expressions must end in the TLD `qjz9zk`.
* The search and replacement expressions must have a one-to-one correspondance: no two search expressions can match the same string, and no two replacement expressions can result in the same string.

### Patches

All of ungoogled-chromium's patches for the Chromium source code are located in `patches/`. The patches in this directory are referenced by config bundles' `patch_order.list` config file.

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

Building the source code consists of the following steps:

1. Apply patches
2. Build GN via `tools/gn/bootstrap/bootstrap.py`
3. Run `gn gen` with the GN flags
4. Build Chromium via `ninja`

Packaging consists of packaging types; each type has differing package outputs and invocation requirements. Some packaging types divide the building and package generation steps; some have it all-in-one. The current packaging types are as follows:

* `archlinux` - Generates a PKGBUILD that downloads, builds, and packages Chromium. Unlike other packaging types, this type does not use the buildspace tree; it is a standalone script that automates the entire process.
* `debian` - Generates `debian` directories for building `.deb.` packages for Debian and derivative systems. There are different variants of Debian packaging scripts known as *flavors*. The current flavors are:
    * (debian codename here) - For building on the Debian version with the corresponding code name. They are derived from Debian's `chromium` package, with only a few modifications. Older codenames are built upon newer ones. These packaging types are intended to be used with derivatives of the `linux_rooted` bundle.
    * `minimal` - For building with a derivative of the `linux_portable` bundle.
* `linux_simple` - Generates two shell scripts for Linux. The first applies patches and builds Chromium. The second packages the build outputs into a compressed tar archive.
* `macos` - Generates a shell script for macOS to build Chromium and package the build outputs into a `.dmg`.

The directories in `resources/packaging` correspond to the packaging type names. The only exception is `shared`, which is reserved for files shared among multiple packaging types.

## buildkit

buildkit is a Python 3 library and CLI application for building ungoogled-chromium. Its main purpose is to setup the buildspace tree and any requested building or packaging scripts from the `resources/` directory.

Use `buildkit-launcher.py` to invoke the buildkit CLI. Pass in `-h` or `--help` for usage details.

For examples of using buildkit's CLI, see [docs/building.md](docs/building.md).

There is currently no API documentation for buildkit. However, all public classes, functions, and methods have docstrings that explain their usage and behavior.

### buildkit design philosophy

buildkit should be simple and transparent instead of limited and intelligent when it is reasonable. As an analogy, buildkit should be like git in terms of the scope and behavior of functionality (e.g. subcommands) and as a system in whole.

buildkit should be as configuration- and platform-agnostic as possible. If there is some new functionality that is configuration-dependent or would require extending the configuration system (e.g. adding new config file types), it is preferred for this to be added to packaging scripts (in which scripts shared among packaging types are preferred over those for specific types).

## Buildspace

Buildspace is a directory that contains all intermediate and final files for building. Its default location is in the repository directory as `buildspace/`. The directory structure is as follows:

* `tree` - The Chromium source tree, which also contains build intermediates.
* `downloads` - Directory containing all files download; this is currently the Chromium source code archive and any potential extra dependencies.
* Packaged build artifacts

    (The directory may contain additional files if developer utilities are used)
