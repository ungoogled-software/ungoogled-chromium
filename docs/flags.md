# List of flags and switches

This is an exhaustive list of command-line switches and flags introduced by ungoogled-chromium.  
Each switch has a corresponding entry on the `chrome://flags` page which can be filtered by searching for `ungoogled-chromium`.  

If a switch requires a value, you must specify it with an `=` sign; e.g. flag `--foo` with value `bar` should be written as `--foo=bar`.

> **NOTE**: If you add a command-line argument that is also in `chrome://flags`, the flag's state will not be indicated in `chrome://flags`. There is no universal way to ensure command-line flags are taking effect, but you can find if they're being seen by checking `chrome://version`.

- ### Available on all platforms

  <code>Switch&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</code> | Description
  -- | --
  `--disable-beforeunload` | Disables JavaScript dialog boxes triggered by `beforeunload`
  `--disable-search-engine-collection` | Disable automatic search engine scraping from webpages.
  `--enable-stacked-tab-strip`<br>`--enable-tab-adjust-layout` | These flags adjust the tab strip behavior. Please note that they are not well tested, so proceed with caution.
  `--extension-mime-request-handling` | Change how extension MIME types (CRX and user scripts) are handled. Acceptable values are `download-as-regular-file` or `always-prompt-for-install`. Leave unset to use normal behavior.
  `--fingerprinting-canvas-image-data-noise` | (Added flag to Bromite feature) Implements fingerprinting deception for Canvas image data retrieved via JS APIs. In the data, at most 10 pixels are slightly modified.
  `--fingerprinting-canvas-measuretext-noise` | (Added flag to Bromite feature) Scale the output values of Canvas::measureText() with a randomly selected factor in the range -0.0003% to 0.0003%, which are recomputed on every document initialization.
  `--fingerprinting-client-rects-noise` | (Added flag to Bromite feature) Implements fingerprinting deception of JS APIs `getClientRects()` and `getBoundingClientRect()` by scaling their output values with a random factor in the range -0.0003% to 0.0003%, which are recomputed for every document instantiation.
  `--hide-crashed-bubble` | Hides the bubble box with the message "Restore Pages? Chromium didn't shut down correctly." that shows on startup after the browser did not exit cleanly.
  `--keep-old-history` | Disables deletion of local browser history after 90 days
  `--max-connections-per-host` | (from Bromite) Configure the maximum allowed connections per host. Valid values are `6` and `15`
  `--omnibox-autocomplete-filtering` | Restrict omnibox autocomplete results to a combination of search suggestions (if enabled), bookmarks, and internal chrome pages.  Accepts `search`, `search-bookmarks`, `search-chrome`, and `search-bookmarks-chrome`.
  `--popups-to-tabs` | Makes popups open in new tabs.

- ### Available only on desktop

  <code>Switch&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</code> | Description
  -- | --
  `--bookmark-bar-ntp` | Sets the visibility of the bookmark bar on the New Tab Page. Only takes the value `never`.
  `--close-confirmation` | Show a warning prompt when closing the browser window. Accepts `last` (prompt when closing the last window with several tabs) and `multiple` (prompt only if more than one window is open). 
  `--close-window-with-last-tab` | Determines whether a window should close once the last tab is closed.  Only takes the value `never`.
  `--pdf-plugin-name` | Sets the internal PDF viewer plugin name. Useful for sites that probe JavaScript API `navigator.plugins`. Supports values `chrome` for Chrome, `edge` for Microsoft Edge. Default value when omitted is Chromium.
  `--remove-grab-handle` | Removes the reserved empty space in the tabstrip for moving the window.
  `--remove-tabsearch-button` | Removes the tabsearch button from the tabstrip.
  `--scroll-tabs` | Determines if scrolling will cause a switch to a neighboring tab if the cursor hovers over the tabs, or the empty space beside the tabs. The flag requires one the values: `always`, `never`, `incognito-and-guest`. When omitted, the default is to use platform-specific behavior, which is currently enabled only on desktop Linux.
  `--show-avatar-button` | Sets visibility of the avatar button. The flag requires one of the values: `always`, `incognito-and-guest` (only show Incognito or Guest modes), or `never`.

  - #### Available only on Windows

    <code>Switch&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</code> | Description
    -- | --
    `--disable-encryption` | Disable encryption of cookies, passwords, and settings which uses a generated machine-specific encryption key. This is used to enable portable user data directories.
    `--disable-machine-id` | Disables use of a generated machine-specific ID to lock the user data directory to that machine. This is used to enable portable user data directories.


## Feature flags

Feature flags are similar to switches with the difference being that they are passed as values for the `--enable-features` switch.  Multiple features can be passed at the same time by separating them with a comma, e.g. `--enable-features=flag1,flag2,flag3`.  
These are also available on the `chrome://flags` page.  

- ### Available on all platforms

  <code>Feature&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</code> | Description
  -- | --
  `SetIpv6ProbeFalse` | Forces the result of the browser's IPv6 probing (i.e. IPv6 connectivity test) to be unsuccessful. This causes IPv4 addresses to be prioritized over IPv6 addresses. Without this flag, the probing result is set to be successful, which causes IPv6 to be used over IPv4 when possible.

- ### Available only on desktop

  <code>Feature&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</code> | Description
  -- | --
  `ClearDataOnExit` | Clears all browsing data on exit.
  `DisableQRGenerator` | Disables the QR generator for sharing page links.
