# List of flags and switches

This is an exhaustive list of command-line switches and `chrome://flags` introduced by ungoogled-chromium:

* `--disable-beforeunload` (Not in `chrome://flags`) - Disables JavaScript dialog boxes triggered by `beforeunload`
* `--disable-encryption` (Windows only, not in `chrome://flags`) - Disable encryption of cookies, passwords, and settings which uses a generated machine-specific encryption key. This is used to enable portable user data directories.
* `--disable-machine-id` (Windows only, not in `chrome://flags`) - Disables use of a generated machine-specific ID to lock the user data directory to that machine. This is used to enable portable user data directories.
* `--disable-search-engine-collection` - Disable automatic search engine scraping from webpages.
* `--enable-stacked-tab-strip` and `--enable-tab-adjust-layout` - These flags adjust the tab strip behavior. `--enable-stacked-tab-strip` is also configurable in `chrome://flags` Please note that they are not well tested, so proceed with caution.
* `--extension-mime-request-handling` - Change how extension MIME types (CRX and user scripts) are handled. Acceptable values are `download-as-regular-file` or `install-always`. Leave unset to use normal behavior. It is also configurable under `chrome://flags`
* `--fingerprinting-canvas-image-data-noise` (Added flag to Bromite feature) - Implements fingerprinting deception for Canvas image data retrieved via JS APIs. In the data, at most 10 pixels are slightly modified.
* `--fingerprinting-canvas-measuretext-noise` (Added flag to Bromite feature) - Scale the output values of Canvas::measureText() with a randomly selected factor in the range -0.0003% to 0.0003%, which are recomputed on every document initialization.
* `--fingerprinting-client-rects-noise` (Added flag to Bromite feature) - Implements fingerprinting deception of JS APIs `getClientRects()` and `getBoundingClientRect()` by scaling their output values with a random factor in the range -0.0003% to 0.0003%, which are recomputed for every document instantiation.
* `--hide-crashed-bubble` (Not in `chrome://flags`) - Hides the bubble box with the message "Restore Pages? Chromium didn't shut down correctly." that shows on startup after the browser did not exit cleanly.
* `--max-connections-per-host` (from Bromite) - Configure the maximum allowed connections per host.
* `--scroll-tabs` - Determines if scrolling will cause a switch to a neighboring tab if the cursor hovers over the tabs, or the empty space beside the tabs. The flag requires one the values: `always`, `never`. When omitted, the default is to use platform-specific behavior, which is currently enabled only on desktop Linux.
* `--set-ipv6-probe-false` - (Not in `chrome://flags`) Forces the result of the browser's IPv6 probing (i.e. IPv6 connectivity test) to be unsuccessful. This causes IPv4 addresses to be prioritized over IPv6 addresses. Without this flag, the probing result is set to be successful, which causes IPv6 to be used over IPv4 when possible.
* `--show-avatar-button` - Sets visibility of the avatar button. The flag requires one of the values: `always`, `incognito-and-guest` (only show Incognito or Guest modes), or `never`.
