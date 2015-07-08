# ungoogled-chromium
**Patches for Google Chromium to remove integration with Google services and add additional features**

### Features

- Disabled background communication with Google servers
- Disabled safe browsing
- Disabled browser sign-in
- Disabled searching in Omnibox
- Disabled automatic formatting of URL in Omnibox
- Disabled JavaScript dialog boxes from showing when a page closes (onbeforeunload dialog boxes)
- Added menu item under "More tools" to clear the HTTP authentication cache on-demand
- Disabled persistent per-site settings in Preferences file
- Disabled extension autoupdating

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

- Disable background communication with translate.9oo91eapis.qjz9zk (when patched with domain-replacement script) when settings are opened
- Make Webstore and extension updating work
- Add Windows support
- Add settings menu to manually edit password database(?)

## Credits

Debian for build scripts <br />
Google for Chromium

## License

Public domain
