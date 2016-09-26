# Frequently Asked Questions

## Can I install extensions from the Chrome Webstore?

Yes, but not via the web interface. Adapted from [inox-patchset](https://raw.githubusercontent.com/gcarq/inox-patchset/master/README.md):

Since there is no Webstore plugin, you cannot install extensions directly from the store, but you can download and install any extension manually.

    https://clients2.google.com/service/update2/crx?response=redirect&prodversion=48.0&x=id%3D[EXTENSION_ID]%26installsource%3Dondemand%26uc

To download a extension just replace [EXTENSION_ID] with the extension-id from the WebStore
(For example cjpalhdlnbpafiamejdnhcphjbkeiagm is the extension id of uBlock Origin).
You have 3 options to install an extension:


* **Drag and drop**

    Download the crx file with the browser, open `chrome://extensions` and drop the file from the download bar into the extensions tab.
    **Note:** Under some circumstances this method does not work on KDE Plasma.


* **Preference file (Linux systems only)**

    For example to install the extension aaaaaaaaaabbbbbbbbbbcccccccccc, create:
    `/usr/share/chromium/extensions/aaaaaaaaaabbbbbbbbbbcccccccccc.json`
    with following content:
    ```json
    {
        "external_crx": "/home/share/extension_1_0_0.crx",
        "external_version": "1.0.0"
    }
    ```
    If you restart Inox the extension should be loaded automatically.

* **Extension loader**

    You can also use [extension-downloader](https://github.com/gcarq/inox-patchset/issues/7), it's a small python script to automate the download.

Keep in mind extensions are not updated automatically, so make sure you update them on a regular base.

## Do plugins work?

Yes. All plugins including PepperFlash and Widevine DRM should work.

## Why are there URLs with the `qjz9zk` domain in them? Why use domain substitution?

`qjz9zk` is the common top-level domain name used by domain substitution. It is a relatively trivial way of disabling unwanted requests and notifying the user if any of these URLs attempt to connect without having to look through the many changes that happen to Chromium each version.
