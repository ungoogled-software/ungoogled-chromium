#!/usr/bin/env python3

# Copyright (c) 2018 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

if __name__ == '__main__':
    import sys
    from pylint import epylint as lint
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    if len(sys.argv) < 2:
        print('Need a path to the module to test')
        exit(1)
    if len(sys.argv) > 2:
        print('Too many arguments: Expected 2, got %s' % len(sys.argv))
        exit(2)
    if not Path(sys.argv[1]).exists():
        print('Module path does not exist')
        exit(3)

    lint.lint(filename=sys.argv[1], options=[
        '--disable=locally-disabled,wrong-import-position',
        '--jobs=4'])
