#!/usr/bin/env python

# Substitute domain names with domain_regex_list for files in domain_substitution_list
# This script is designed to run cross-platform
# Usage: evaluate_domain_substitution_list.py file_list

import sys
import os
import os.path

if __name__ == "__main__":
    if not len(sys.argv) > 2:
        print "Usage: {} domain_regex_list domain_substitution_list".format(sys.argv[0])
        exit(1)
    regex_list_path = sys.argv[1]
    file_list_path = sys.argv[2]

    # TODO: Parse domain_regex_list

    with open(file_list_path) as file_list:
        for line in file_list:
            line = line.replace("\n", "")
            if len(line) > 0:
                line = os.path.normpath(line)
                if os.path.isfile(line):
                    # TODO: Checking and substitution
                else:
                    print "Not a file: {}".format(line)
    print "Done evaluating {sub} with {regex}".format(sub=file_list_path, regex=regex_list_path)
