# Building ungoogled-chromium

This document contains building instructions for supported platforms and configurations.

For configurations, you may try augmenting the standard Chromium build procedure with tools from ungoogled-chromium; please read [design.md](design.md) for more details.

## IMPORTANT - Please read this section first

**Statuses of platform support**: Because platform support varies across stable versions, [this Wiki page tracks platform support for the current stable](//github.com/Eloston/ungoogled-chromium/wiki/statuses). *Please check the status before attempting a build or posting an issue*.

**Choosing a version**: *It is highly recommended to choose a tag version for building.* `master` and other branches are not guarenteed to be in a working state.

## Contents

* [Debian and its derivatives](#debian-and-its-derivatives)
* [Windows](#windows)
* [macOS](#macos)
* [Arch Linux](#arch-linux)
* [OpenSUSE](#opensuse)
* [Any Linux distribution](#any-linux-distribution)
* [Google Cloud Computing](#google-cloud-computing)

## Debian and its derivatives

These instructions will create `.deb` packages. It uses ungoogled-chromium's variation of Debian's `debian` directory.

The build should work on CPU architecture `amd64`

* `i386`, `arm64`, `armhf`, and cross-compilation are unsupported at this time due to the lack of contributors.

The final size of the sandbox with build artifacts is over 5 GB. On 64-bit systems with enough RAM, it can be built entirely within `tmpfs` without swap memory.

### Hardware requirements

* For 64-bit systems, at least 8 GB of RAM is highly recommended (as recommended in the Chromium source tree under `docs/linux_build_instructions.md`).
    * It may be possible to reduce RAM comsumption with a lower value for the GN flag `jumbo_file_merge_limit` (documented in the Chromium source code under `docs/jumbo.md`).
    * Debian's `chromium` package version `69.0.3497.81-1` uses a value of: 12
* Filesystem space: 8 GB is the bare minimum. More is safer.

### Setting up the build environment

Install base requirements: `# apt install packaging-dev python3 ninja-build`

On Debian 9 (stretch), `stretch-backports` APT source is used to obtain LLVM 6.0. Do NOT use debhelper 11 from backports, as it will be incompatible with other dpkg tools.

### Building locally

```sh
# Run from inside the clone of the repository
mkdir -p build/src
./get_package.py PACKAGE_TYPE_HERE build/src/debian
cd build/src
# Use dpkg-checkbuilddeps (from dpkg-dev) or mk-build-deps (from devscripts) to check for additional packages.
# If necessary, change the dependencies in debian/control to accomodate your environment.
# If necessary, modify AR, NM, CC, and CXX variables in debian/rules
debian/rules setup-local-src
dpkg-buildpackage -b -uc
```

where `PACKAGE_TYPE_HERE` is one of the following:

* `debian_stretch` for Debian 9 (stretch)
* `debian_buster` for Debian 10 (buster)
* `ubuntu_bionic` for Ubuntu 18.04 (bionic)
* `debian_minimal` for any other Debian-based system that isn't based on one of the above versions.

Packages will appear under `build/`.

### Building via source package

```sh
# Run from inside the clone of the repository
mkdir -p build/src
./get_package.py PACKAGE_TYPE_HERE build/src/debian
cd build/src
# If necessary, change the dependencies in debian/control to accomodate your environment.
# If necessary, modify AR, NM, CC, and CXX variables in debian/rules
debian/rules get-orig-source
debuild -S -sa
```

(`PACKAGE_TYPE_HERE` is the same as above)

Source package files should appear in `build/`

## Windows

Google only supports [Windows 7 x64 or newer](https://chromium.googlesource.com/chromium/src/+/64.0.3282.168/docs/windows_build_instructions.md#system-requirements). These instructions are tested on Windows 7 Professional x64.

NOTE: The default configuration will build 64-bit binaries for maximum security (TODO: Link some explanation). This can be changed to 32-bit by following the instructions in `build.py`

### Setting up the build environment

#### Setting up Visual Studio

[Follow the official Windows build instructions](https://chromium.googlesource.com/chromium/src/+/64.0.3282.168/docs/windows_build_instructions.md#visual-studio).

**IMPORTANT**: According to [a Chromium developer in Google Groups](https://groups.google.com/a/chromium.org/d/msg/chromium-dev/PsqFiJ-j5B4/9wO3wflWCQAJ), due to bugs in the 10.0.16299.15 SDK (that comes with Visual Studio 2017 as of Feburary 2018) *will not work* to build Chromium. The 10.0.15063 SDK must be downloaded and installed. This can be downloaded from the [Windows SDK Archive](https://developer.microsoft.com/en-us/windows/downloads/sdk-archive).

When installing the SDK, the "Debugging Tools for Windows" feature must be enabled. Visual Studio 2017 does not enable this by default, so it has to be added in by selecting "Modify" on the SDK entry in "Add or remove programs".

#### Other build requirements

**IMPORTANT**: Currently, the `MAX_PATH` path length restriction (which is 260 characters by default) must be lifted in order for buildkit to function properly. One such setup that works is Windows 10 (which added this option since Anniversary) with Python 3.6 or newer from the official installer (which contains the manifest files that allow use of long file paths). Other possible setups are being discussed in [Issue #345](https://github.com/Eloston/ungoogled-chromium/issues/345).

1. Setup the following:

    * 7-zip
    * Python 2.7 (for scripts in the Chromium source tree), with pypiwin32 module (`pip install pypiwin32`)
    * Python 3.5+ (for build and packaging scripts used below)

2. Make sure Python 2.7 is set in the user or system environment variable `PATH` as `python`.

### Setup and build

NOTE: The commands below assume the `py` command was installed by Python 3 into `PATH`. If this is not the case, then substitute it with the command to invoke **Python 3**.

Run in `cmd.exe`:

```cmd
mkdir build\src
py get_package.py windows build\src\ungoogled_packaging
cd build\src
py ungoogled_packaging\build.py
py ungoogled_packaging\package.py
```

A zip archive will be created in `build\src`

## macOS

### Software requirements

* macOS 10.12+
* Xcode 8-9
* Homebrew
* Perl (for creating a `.dmg` package)

### Setting up the build environment

1. Install Ninja via Homebrew: `brew install ninja`
2. Install GNU coreutils (for `greadlink` in packaging script): `brew install coreutils`

### Building

```sh
# Run from inside the clone of the repository
mkdir -p build/src/ungoogled_packaging
./get_package.py macos build/src/ungoogled_packaging
cd build/src
./ungoogled_packaging/build.sh
```

A `.dmg` should appear in `build/`

## Arch Linux

A PKGBUILD is used to build on Arch Linux. It handles downloading, unpacking, building, and packaging.

Requirements: Python 3 is needed to generate the PKGBUILD. The PKGBUILD contains build dependency information.

Generate the PKGBUILD:

```
./get_package.py archlinux ./
```

A PKGBUILD will be generated in the current directory. It is a standalone file that can be relocated as necessary.

## openSUSE

Tested on openSUSE Leap 42.3

### Setting up the build environment

Install the following packages : `# sudo zypper install perl-Switch dirac-devel hunspell-devel imlib2-devel libdc1394 libdc1394-devel libavcodec-devel yasm-devel libexif-devel libtheora-devel schroedinger-devel minizip-devel python-beautifulsoup4 python-simplejson libvdpau-devel slang-devel libjack-devel libavformat-devel SDL-devel ninja binutils-gold bison cups-devel desktop-file-utils fdupes flex gperf hicolor-icon-theme libcap-devel libelf-devel libgcrypt-devel libgsm libgsm-devel libjpeg-devel libpng-devel libva-devel ncurses-devel pam-devel pkgconfig re2-devel snappy-devel update-desktop-files util-linux wdiff alsa Mesa-dri-devel cairo-devel libavutil-devel libavfilter-devel libdrm2 libdrm-devel libwebp-devel libxslt-devel libopus-devel rpm-build` 

**Note**: There may be additional package requirements besides those listed above, if so they will be listed when using `rpmbuild` to create the ungoogled-chromium package. 

Follow the following guide to set up Python 3.6.4: [https://gist.github.com/antivanov/01ed4eac2d7486a170be598b5a0a4ac7](https://gist.github.com/antivanov/01ed4eac2d7486a170be598b5a0a4ac7) 

As of Chromium 66.0.3359.117, llvm, lld and clang version 6 or greater is required to avoid compiler errors.

### Generate packaging scripts

Before executing the following commands, make sure you are using python 3.6 as was mentioned in the build environment section of this guide.

```sh
# Run from inside the clone of the repository
mkdir -p build/{download_cache,src}
# TODO: The download commands should be moved into the packaging scripts
./get_package.py opensuse build/src/ungoogled_packaging
```

Before proceeding to the build chromium, open a new tab or otherwise exit the python 3.6 virtual environment, as it will cause errors in the next steps.

### Setting up environment for RPM build

Note: This section only has to be performed once.

Execute the following commands:

```sh
mkdir -p ~/rpm/{BUILD,RPMS,SOURCES,SPECS,SRPMS}

cat <<EOF >~/.rpmmacros
%HOME       %{expand:%%(cd; pwd)}
%_topdir    %{HOME}/rpm
EOF
```

### Invoking build and installing package

```sh
# Run from inside the clone of the repository
cd build/src
./ungoogled_packaging/setup.sh
cd ~/rpm
rpmbuild -v -bb --clean SPECS/ungoogled-chromium.spec
```

The RPM will be located in `~/rpm/RPMS/{arch}/` once rpmbuild has finished. It can be installed with the command `sudo rpm -i {path to RPM}`

## Any Linux distribution

These instructions will build packages compatible with any Linux distribution that Chromium supports. Unlike distro-specific packages, they are portable and have minimal dependencies with system libraries (just as in regular Chromium).

### Hardware requirements

* For 64-bit systems, at least 8 GB of RAM is highly recommended (per the document in the Chromium source tree under `docs/linux_build_instructions.md`).
    * It may be possible to reduce RAM comsumption with a lower value for the GN flag `jumbo_file_merge_limit` (documented in the Chromium source code under `docs/jumbo.md`).
* At least 8 GB of filesystem space. 16 GB should be safe.

### Software requirements

TODO: Document all libraries and tools needed to build. For now, see the build dependencies for Debian systems.

* Python 3 (tested on 3.5) for buildkit
* Python 2 (tested on 2.7) for building GN and running other build-time scripts
* [Ninja](//ninja-build.org/) for running the build command
* LLVM 6.0 (including Clang and LLD)

For Debian-based systems, these can be installed via apt: `# apt install clang-6.0 lld-6.0 llvm-6.0-dev python python3 ninja-build`

* Some systems, like Debian 9 (stretch), don't include LLVM tools in the default repositories. Debian 9 (stretch) has LLVM 6.0 in the backports repository.
* Alternatively for systems where backports is not an option, LLVM tools can be installed after adding [the LLVM APT repo](//apt.llvm.org/).

### Build a tar archive

```sh
# Run from inside the clone of the repository
mkdir -p build/src
./get_package.py linux_simple build/src/ungoogled_packaging
cd build/src
# Use "export ..." for AR, NM, CC, CXX, or others to specify the compiler to use
# It defaults to LLVM tools. See ./ungoogled_packaging/build.sh for more details
./ungoogled_packaging/build.sh
./ungoogled_packaging/package.sh
```

A compressed tar archive will appear in `build/src/ungoogled_packaging/`

### Building an AppImage, Flatpak, or Snap package

TODO. See [Issue #36](//github.com/Eloston/ungoogled-chromium/issues/36)

### Building Portable Version On Fedora 

Fedora is using a new version of glibc, so if you are planning to distribute the portable binary for distro other than fedora, it's not a good idea to build it with fedora

For information purpose i used Scaleway Cloud Services with a VM running Fedora v28 to build/test those instructions

Update & install needed packages
```
dnf update 
dnf install wget git patch nano ninja-build python36
dnf builddep chromemium
dnf install perl-Switch dirac-devel hunspell-devel imlib2-devel libdc1394 libdc1394-devel libavcodec-devel yasm-devel libexif-devel libtheora-devel schroedinger-devel minizip-devel libvdpau-devel slang-devel libjack-devel libavformat-devel SDL-devel ninja binutils-gold bison cups-devel desktop-file-utils fdupes flex gperf hicolor-icon-theme libcap-devel libelf-devel libgcrypt-devel libgsm libgsm-devel libjpeg-devel libpng-devel libva-devel ncurses-devel pam-devel pkgconfig re2-devel snappy-devel update-desktop-files util-linux wdiff alsa Mesa-dri-devel cairo-devel libavutil-devel libavfilter-devel libdrm2 libdrm-devel libwebp-devel libxslt-devel libopus-devel rpm-build --skip-broken
yum install clang*
yum install llvm llvm-static llvm-devel ninja*
```
Clone sources
```
git clone https://github.com/Eloston/ungoogled-chromium.git
cd ungoogled-chromium
```
Prepare sources
```
mkdir -p build/src
./get_package.py linux_simple build/src/ungoogled_packaging
cd build/src
```
Edit `./ungoogled_packaging/build.sh ` and remove the last line starting with ninja

Prepare build 
```
./ungoogled_packaging/build.sh
```

Build (Note that `-j48` is for a cpu with 48 cores so update that number according to how many build thread you want to run at the same time)
```
ninja -j48 -C out/Default chrome chrome_sandbox chromedriver
```

Create the tar archive with the portable chromium
```
./ungoogled_packaging/package.sh
```

### Building Portable Version On OpenSuse 

Update your distro
```
zypper update
```

If you are willing to deploy your built version check your glibc version because a too new version will made your build not usable
```
ldd --version
```

Add repo needed for clang6 python6 and llvm6
```
zypper addrepo -f https://download.opensuse.org/repositories/devel:/languages:/python:/Factory/openSUSE_Leap_42.3/ new-devels-python
zypper addrepo -f https://download.opensuse.org/repositories/devel:/tools:/compiler/openSUSE_Leap_42.3/ new-devels-clang6llvm
zypper addrepo -f https://download.opensuse.org/repositories/home:/Pharaoh_Atem:/DNF_SUSE/openSUSE_Leap_42.3/ dnf-manager
```
Check added repos 
```
zypper repos -d
```

Install needed packages (Note that this list is exhaustive i did not have the time to shrink it to just needed packages) 
`zypper install perl-Switch dirac-devel hunspell-devel imlib2-devel libdc1394 libdc1394-devel libavcodec-devel yasm-devel libexif-devel libtheora-devel schroedinger-devel minizip-devel python-beautifulsoup4 python-simplejson libvdpau-devel slang-devel libjack-devel libavformat-devel SDL-devel ninja binutils-gold bison cups-devel desktop-file-utils fdupes flex gperf hicolor-icon-theme libcap-devel libelf-devel libgcrypt-devel libgsm libgsm-devel libjpeg-devel libpng-devel libva-devel ncurses-devel pam-devel pkgconfig re2-devel snappy-devel update-desktop-files util-linux wdiff alsa Mesa-dri-devel cairo-devel libavutil-devel libavfilter-devel libdrm2 libdrm-devel libwebp-devel libxslt-devel libopus-devel rpm-build`

`zypper in subversion pkg-config python perl bison flex gperf mozilla-nss-devel glib2-devel gtk-devel wdiff lighttpd gcc gcc-c++ gconf2-devel mozilla-nspr mozilla-nspr-devel php5-fastcgi alsa-devel libexpat-devel libjpeg-devel libbz2-devel`

`zypper install git libllvm python-hawkey python-librepo python-gpgme python-iniparse python-h5py python2-h5py lld6 libllvm llvm6 clang6 *alsa* builder python-curses python3-pkgconfig *pkgconfig* *buildkit* *liboil* lib64nss *llvm6*devel* llvm-6.0-dev *nss*dev* python3-packaging python3-setuptools *atk* nano gtk-*devel* gtk2-*devel* pciuti*dev* *lxtst*dev* *libXtst*dev* libXtst-dev *scrnsaver* *libXss*dev* *xss*dev* *screens*dev* *scrns*dev* *x11*dev* *pulse*dev* nss_ldap-265-35.14.x86_64 python-base-2.7.15-112.1.x86_64 python-xml-2.7.15-112.1.x86_64 python-2.7.15-105.1.x86_64 libpython2_7-1_0-2.7.15-112.1.x86_64 python-pyliblzma chromium`

Install new python version from sources (3.6.6) note that i am using 24 cpu to build, on a normal machine just replace `make -j24` with `make`
```
wget https://www.python.org/ftp/python/3.6.6/Python-3.6.6.tgz
tar -xvf Python-3.6.6.tgz 
cd Python-3.6.6/
./configure
make -j24
make install
mv /usr/bin/python3 /usr/bin/python3old
ln -s /usr/local/bin/python3 /usr/bin/python3
ln -s /usr/local/bin/python3 /usr/bin/python3.6
```
Getting sources (Note that this instruction will build v68.0.3440.106-2)
```
mkdir chrome
cd chrome
git clone https://github.com/Eloston/ungoogled-chromium.git
cd ungoogled*
git checkout tags/68.0.3440.106-2
```
Setup sources
```
mkdir -p build/src
./get_package.py linux_simple build/src/ungoogled_packaging
cd build/src
```
Edit build script to match your CPU `nano ./ungoogled_packaging/build.sh` and comment or remove the last line starting with ninja 

Prepare to build
```
./ungoogled_packaging/build.sh
```

Build (Note that `-j48` is for a cpu with 48 cores so update that number according to how many build thread you want to run at the same time)
```
ninja -j48 -C out/Default chrome chrome_sandbox chromedriver
```

Create the tar archive with the portable chromium
```
./ungoogled_packaging/package.sh
```

## Google Cloud Computing
**Infos :**
Build it in 10 min with google cloud computing; Google provide a VM/Servers services with it's cloud computing service, also it offer more than 200 euros trial to new users, so why not use a powerfull machine to build this beast in a reasonable time and also may be have a kind of cli instruction to make it a little more easy for contributors 

**Where :**
Just create an account at https://cloud.google.com/

**Infos II :** 
I managed to build v68 there against glibc v2.22 (for portability) i used an opensuse vm

 **How To :** 
After creating a new account or using your existing one 
install gcloud from here https://cloud.google.com/sdk/install or use a portable version or...

Create a virtual machine with opensuse (Note that opensuse vm can only be ceated with the gcloud command because opensuse image is a community image so its not listed on the web interface. also note that i am using a special config with 24 cpu cores etc. so update the command to your needs)
```
./gcloud compute instances create osuse-leap-42-3-2018 --image-family opensuse-leap --image-project opensuse-cloud --zone europe-west4-b --boot-disk-type pd-ssd --boot-disk-device-name=bootssd --boot-disk-size=40GB --min-cpu-platform 'Intel Skylake' --custom-cpu 24 --custom-memory 64GB
```

If you want to remote your VM directly with ssh and not with the web terminal you will need to add an ssh key (How to generate a key is explained here https://cloud.google.com/compute/docs/instances/adding-removing-ssh-keys)
```
./gcloud compute config-ssh --ssh-key-file /home/path/to/your/ssh/key.key
```

Connect to your vm 
```
ssh 35.0.0.54 -i /home/path/to/your/ssh/key.key
sudo su 
```

You can then follow building instructions [Building Portable Version On OpenSuse](#building-portable-version-on-opensuse) or else depending on your vm configuration

