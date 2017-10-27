# Frequently Asked Questions

* [Can I install extensions from the Chrome Webstore?](#can-i-install-extensions-from-the-chrome-webstore)
* [Do plugins work?](#do-plugins-work)
* [Why are there URLs with the `qjz9zk` domain in them? Why use domain substitution?](#why-are-there-urls-with-the--qjz9zk--domain-in-them--why-use-domain-substitution)
* [Does domain substitution break the HSTS preload list?](#does-domain-substitution-break-the-hsts-preload-list)
* [Why is Safe Browsing disabled?](#why-is-safe-browsing-disabled)
* [How do I install Flash player?](#how-do-i-install-flash-player)
* [How do I install Widevine CDM?](#how-do-i-install-widevine-cdm)
* [How do I get the Namespace Sandbox to work on Linux?](#how-do-i-get-the-namespace-sandbox-to-work-on-linux)
* [How to get FIDO U2F security keys to work in Google sign in?](#how-to-get-fido-u2f-security-keys-to-work-in-google-sign-in)

## Can I install extensions from the Chrome Webstore?

Yes, but not via the web interface. Adapted from [inox-patchset](https://raw.githubusercontent.com/gcarq/inox-patchset/master/README.md):

Since there is no Webstore plugin, you cannot install extensions directly from the store, but you can download and install any extension manually.

    https://clients2.google.com/service/update2/crx?response=redirect&prodversion=48.0&x=id%3D[EXTENSION_ID]%26installsource%3Dondemand%26uc

To download a extension just replace [EXTENSION_ID] with the extension-id from the WebStore
(For example cjpalhdlnbpafiamejdnhcphjbkeiagm is the extension id of uBlock Origin).
You have 4 options to install an extension:

* **User script**

    You can use [this user script](http://chromium-crx.stuff.admicos.cf/get.user.js), which will add a button to the Chrome Webstore so the CRX file can be downloaded and installed.

    Script written and provided by Admicos in [#134](//github.com/Eloston/ungoogled-chromium/issues/134)

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
    If you restart Inox, the extension should be loaded automatically.

* **Extension loader**

    You can also use [extension-downloader](https://github.com/gcarq/inox-patchset/issues/7), it's a small python script to automate the download.

Keep in mind extensions are not updated automatically, so make sure you update them on a regular base.

## Do plugins work?

Yes. All plugins including PepperFlash and Widevine DRM should work. See the relevant question for specific installation instructions.

## Why are there URLs with the `qjz9zk` domain in them? Why use domain substitution?

`qjz9zk` is the common top-level domain name used by domain substitution. It is a relatively trivial way of disabling unwanted requests and notifying the user if any of these URLs attempt to connect without having to look through the many changes that happen to Chromium each version.

## Does domain substitution break the HSTS preload list?

No, the list (which is located in `net/http/transport_security_state_static.json`) is explicitely excluded when generating the domain substitution list. In `developer_utilities/update_helper.py`, see the  `generate_domain_substitution_list()` function for what files are excluded from domain substitution.

## Why is Safe Browsing disabled?

See [this Wikipedia article](//en.wikipedia.org/wiki/Google_Safe_Browsing) for info about Safe Browsing.

Safe Browsing communicates with Google servers in order to download the blacklists. If you are looking for a feature like Safe Browsing, I recommend uBlock Origin or uMatrix.

## How do I install Flash player?

Adobe's version of Flash player (as opposed to Google's Flash player bundled with Chrome) on [Windows and macOS has an auto-update feature](https://helpx.adobe.com/flash-player/kb/flash-player-background-updates.html). Linux users will have to install updates manually, or use a PPAPI Flash player package available from their distribution. The following instructions are for installing Adobe's version of Flash player.

1. Go to https://get.adobe.com/flashplayer/otherversions/
2. Select the target platform for running Flash in Step 1.
3. For Step 2, select one of the following:
    * macOS: `FP 23 Mac for Opera and Chromium - PPAPI` (or the latest version)
    * Windows: `FP 23 for Opera and Chromium - PPAPI` (or the latest version)
    * Linux: `FP 23.0 for other Linux 64-bit (.tar.gz) - PPAPI` (or latest version and appropriate CPU architecture)
4. Click the "Download now" button, then install.

There are also ways to get Google's Flash player or other versions. See http://chromium.woolyss.com/#flash for more details.

## How do I install Widevine CDM?

These instructions are platform-specific.

**WARNING**: For all platforms, it is recommended to download the Google Chrome version that has the same major version as ungoogled-chromium. Otherwise, there may be stability issues or crashes.

### Linux

1. [Download the latest Google Chrome for Linux (.deb file)](https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb)
2. Inside `data.tar.xz`, extract `./opt/google/chrome/libwidevinecdm.so`
3. Using the extracted `libwidevinecdm.so`, replace the existing file of the same name bundled with ungoogled-chromium

### Windows

TODO

### macOS

This applies to version `55.0.2883.95`. In case you're using a different version, make sure to edit the command accordingly.

1. [Download the latest Google Chrome for macOS (.dmg file)](https://dl.google.com/chrome/mac/stable/GGRO/googlechrome.dmg)
2. Put the downloaded `Google Chrome.app` and ungoogled-chromium's `Chromium.app` in the same folder
3. Run the following command in the Terminal:

`cp -R Google\ Chrome.app/Contents/Versions/55.0.2883.95/Google\ Chrome\ Framework.framework/Libraries/WidevineCdm Chromium.app/Contents/Versions/55.0.2883.95/Chromium\ Framework.framework/Libraries/`

Note that there is no slash after `WidevineCdm`.

## How do I get the Namespace Sandbox to work on Linux?

Enable the kernel option `unprivileged_userns_clone`

## How to get FIDO U2F security keys to work in Google sign in?

Google sign in uses a specific extension to access the security key's information. You'll need to install [this extension](https://chrome.google.com/webstore/detail/gnubbyd/beknehfpfkghjoafdifaflglpjkojoco) to make this function. After installation you might need to restart your computer to make it work.
