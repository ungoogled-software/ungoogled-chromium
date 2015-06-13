# ungoogled-chromium
**Patches for Google Chromium to remove integration with Google services and add additional features**

### Features

- Disabled background communication with Google servers
- Disabled safe browsing
- Disabled browser sign-in
- Disabled searching in Omnibox
- Disabled automatic formatting of URL in Omnibox
- Disabled JavaScript dialog boxes from showing when a page is closing
- Added menu item under "More tools" to clear the HTTP authentication cache on-demand
- Disabled persistent per-site settings in Preferences file
- Includes Preferences file with preset settings

## Building

Right now, only Debian build scripts are provided. Windows build scripts will be added in the future.

### Debian and derivatives
**NOTE:** Tested on Debian Jessie 64-bit

    mkdir chromium
    cd chromium
    git clone https://github.com/Eloston/ungoogled-chromium.git src
    cd src
    ./debian/rules download-source
    # Run dpkg-checkbuilddeps to find packages needed for building
    dpkg-buildpackage -b -uc

Debian packages will appear under chromium/

## TODO

- Add the setuid sandbox as a separate Debian package
- Add additional patches to disable connections with clients2.google.com
- Improve current patches
- Add Windows support
- Add settings menu to manually edit credentials database(?)

## Credits

Debian for build scripts
Google for Chromium

