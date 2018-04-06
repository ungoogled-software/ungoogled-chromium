#!/bin/sh

# Chromium launcher

# Authors:
#  Fabien Tassin <fta@sofaraway.org>
# License: GPLv2 or later

APPNAME=chromium
LIBDIR=/usr/lib/chromium
GDB=/usr/bin/gdb

usage () {
  echo "$APPNAME [-h|--help] [-g|--debug] [options] [URL]"
  echo
  echo "        -g or --debug           Start within $GDB"
  echo "        -h or --help            This help screen"
}

# FFmpeg needs to know where its libs are located
if [ "Z$LD_LIBRARY_PATH" != Z ] ; then
  LD_LIBRARY_PATH=$LIBDIR:$LD_LIBRARY_PATH
else
  LD_LIBRARY_PATH=$LIBDIR
fi
export LD_LIBRARY_PATH

# in case chromium runs in a Wayland session ensure GTK falls back to X11
# if we are in a X-session, there is no difference
export GDK_BACKEND=x11

# xdg-settings should in PATH
PATH=$PATH:$LIBDIR
export PATH

want_debug=0
while [ $# -gt 0 ]; do
  case "$1" in
    -h | --help | -help )
      usage
      exit 0 ;;
    -g | --debug )
      want_debug=1
      shift ;;
    -- ) # Stop option prcessing
      shift
      break ;;
    * )
      break ;;
  esac
done

# Setup the default profile if this is none
# Set the default theme as GTK+ with system window decoration
if [ ! -d ~/.config/chromium/Default ]; then
    mkdir -p ~/.config/chromium/Default
    cp /etc/chromium/master_preferences ~/.config/chromium/Default/Preferences
fi

# Allow users to override command-line options
# Based on Gentoo's chromium package (and by extension, Debian's)
if [ -f /etc/default/chromium ]; then
	. /etc/default/chromium
fi

# Detect if PepperFlash has been installed (based on the package in packman)
# If so, automatically enable it
if [ -f /usr/lib/chromium/PepperFlash/libpepflashplayer.so ]; then
      PEPPER_FLASH_VERSION=$(grep '"version":' /usr/lib/chromium/PepperFlash/manifest.json| grep -Po '(?<=version": ")(?:\d|\.)*')
      PEPPERFLASH="--ppapi-flash-path=/usr/lib/chromium/PepperFlash/libpepflashplayer.so --ppapi-flash-version=$PEPPER_FLASH_VERSION"
fi

# Prefer user defined CHROMIUM_USER_FLAGS (from env) over system
# default CHROMIUM_FLAGS (from /etc/chromium/default)
CHROMIUM_FLAGS=${CHROMIUM_USER_FLAGS:-$CHROMIUM_FLAGS}

if [ $want_debug -eq 1 ] ; then
  if [ ! -x $GDB ] ; then
    echo "Sorry, can't find usable $GDB. Please install it."
    exit 1
  fi
  tmpfile=`mktemp /tmp/chromiumargs.XXXXXX` || { echo "Cannot create temporary file" >&2; exit 1; }
  trap " [ -f \"$tmpfile\" ] && /bin/rm -f -- \"$tmpfile\"" 0 1 2 3 13 15
  echo "set args ${1+"$@"}" > $tmpfile
  echo "# Env:"
  echo "#     LD_LIBRARY_PATH=$LD_LIBRARY_PATH"
  echo "$GDB $LIBDIR/$APPNAME -x $tmpfile"
  $GDB "$LIBDIR/$APPNAME" -x $tmpfile
  exit $?
else
  exec $LIBDIR/$APPNAME ${PEPPERFLASH} "--password-store=detect" "--enable-threaded-compositing" "--ui-disable-partial-swap" ${CHROMIUM_FLAGS} "$@"
fi
