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
**NOTE:** Tested on Debian Stretch 64-bit

    git clone https://github.com/Eloston/ungoogled-chromium.git
    cd ungoogled-chromium
    # Run dpkg-checkbuilddeps to find packages needed for building
    ./build.sh

Debian packages will appear under ungoogled-chromium/build-sandbox/

## TODO

- Remove attempted communication with `www.95stat1c.qjz9zk` on startup
- Add Windows support
- Add settings menu to manually edit password database(?)

## Credits

Debian for build scripts <br />
Google for Chromium

## License

Public domain
