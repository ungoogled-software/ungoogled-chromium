# Design and implementation notes

Configuration flags, patches, and build script settings are stored in the `resources` directory. The `resources` directory consists of the following:
* `configs` - GN flags, domain substitution lists, cleaning lists, and the patches to apply
* `patches` - Contains all of the patches used in `configs`
* `packaging` - Files used in producing build scripts (mainly for packaging)

There are currently two source-processing scripts:
* Source cleaner - Used to clean out binary files (i.e. do not seem to be human-readable text files, except a few required for building)
* Domain substitution - Used to replace Google and other domains in the source code to eliminate communication not caught by the patches and build flags.

These processing scripts are a part of the build system.

## `utilikit`: The building system

`utilikit` is a custom set of command-line tools (i.e. a kit of utilities) to assist in building Chromium with the modifications from ungoogled-chromium.

### List of utilities

All utilities have built-in command-line help associated with them. Pass in `-h` or `--help` for more details

* `check_requirements.py` - Checks if the build environment is setup correctly
* `prepare_sources.py` - Downloads, extracts, and runs source cleaning over the Chromium source archive. Also downloads extra dependencies if required.
* `clean_sources.py` - Cleans the source tree (not necessary if using `prepare_sources.py`)
* `substitute_domains.py` - Substitutes domains in the source tree
* `build_gn.py` - Wrapper script around the GN bootstrap script
* `generate_build_files.py` - Generates build and packaging scripts
* `archive_packager.py` - Creates an archive of the build output using `FILES.cfg`
* `export_resources.py` - Exports build flags, patches, domain substitution file list, and source cleaning file list for a configuration

## Contents of a directory in `resources/configs`

* `metadata.ini` - Metadata about the configuration. This includes (but is not limited to) the other configurations that it inherits.
* `cleaning_list` - (Used for source cleaning) A list of files to be excluded during the extraction of the Chromium source
* `domain_regex_list` - (Used for domain substitution) A list of regular expressions that define how domains will be replaced in the source code
* `domain_substitution_list` - (Used for domain substitution) A list of files that are processed by `domain_regex_list`
* `extra_deps.ini` - Contains info to download extra dependencies needed for the platform but not included in the main Chromium source archive
* `gn_flags` - A list of GN flags to use for building.
* `patch_order` - The patches and ordering to apply them in.

All of these files are human-readable, but they are usually processed by the Python building system. See the Building section below for more information.

## Contents of `resources/patches`

* `debian/` - Contains patches from Debian's Chromium.
    * Patches are not touched unless they do not apply cleanly onto the version of Chromium being built
    * These patches are not Debian-specific. For those, see the `resources/debian/patches` directory
* `inox-patchset/` - Contains a modified subset of patches from Inox patchset.
    * Some patches such as those that change branding are omitted
    * Patches are not touched unless they conflict with Debian's patches
    * Patches are from [inox-patchset's GitHub](//github.com/gcarq/inox-patchset)
    * [Inox patchset's license](//github.com/gcarq/inox-patchset/blob/master/LICENSE)
* `iridium-browser` - Contains a modified subset of patches from Iridium Browser.
    * Some patches such as those that change branding or URLs to point to Iridium's own servers are omitted
    * Patches are not touched unless they conflict with Debian's or Inox's patches
    * Patches are from the `patchview` branch of Iridium's Git repository. [Git webview of the patchview branch](//git.iridiumbrowser.de/cgit.cgi/iridium-browser/?h=patchview)
* `ungoogled-chromium/` - Patches from ungoogled-chromium developers.
