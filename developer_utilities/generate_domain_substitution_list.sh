#!/bin/bash

# A script that prints a list of files containing domains to be replaced
# This script's output is domain_substitution_list

# TODO: Construct grep command from entries in domain_regex_list
read -r -d '' print_if_match << EOF
if grep -qE \
-e 'google([A-Za-z\-]*)\.com' \
-e 'gstatic([A-Za-z\-]*)\.com' \
-e 'chrome([A-Za-z\-]*)\.com' \
-e 'chromium([A-Za-z\-]*)\.org' \
-e 'mozilla([A-Za-z\-]*)\.org' \
-e 'facebook([A-Za-z\-]*)\.com' \
-e 'appspot([A-Za-z\-]*)\.com' \
-e 'youtube([A-Za-z\-]*)\.com' \
-e 'ytimg([A-Za-z\-]*)\.com' \
-e 'gmail([A-Za-z\-]*)\.com' \
-e 'doubleclick([A-Za-z\-]*)\.net' \
-e 'googlezip\.net' \
-e 'beacons([1-9]?)\.gvt([1-9]?)\.com' \
-e 'ggpht\.com' \
-e 'microsoft\.com' '{}'
then
printf '{}\n';
fi
EOF

find . -path ./debian -prune \
-o -path ./.pc -prune \
-o -path './components/test/*' -prune \
-o -type f \( -name "*.h" \
    -o -name "*.hh" \
    -o -name "*.hpp" \
    -o -name "*.hxx" \
    -o -name "*.cc" \
    -o -name "*.cpp" \
    -o -name "*.cxx" \
    -o -name "*.c" \
    -o -name "*.h" \
    -o -name "*.json" \
    -o -name "*.js" \
    -o -name "*.html" \
    -o -name "*.htm" \
    -o -name "*.py*" \
    -o -name "*.grd" \
    -o -name "*.sql" \
    -o -name "*.idl" \
    -o -name "*.mk" \
    -o -name "*.gyp*" \
    -o -name "Makefile" \
    -o -name "makefile" \
    -o -name "*.txt" \
    -o -name "*.xml" \
    -o -name "*.mm" \
    -o -name "*.jinja*" \) \
-printf '%P\n' | xargs -L1 -I{} sh -c "$print_if_match"
