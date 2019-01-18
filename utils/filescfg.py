#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

# Copyright (c) 2018 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""
FILES.cfg processing and packaging
"""

from pathlib import Path


def filescfg_generator(cfg_path, build_outputs, cpu_arch):
    """
    Generator that yields pathlib.Path relative to the build outputs according to FILES.cfg

    cfg_path is a pathlib.Path to the FILES.cfg
    build_outputs is a pathlib.Path to the build outputs directory.
    cpu_arch is a platform.architecture() string
    """
    resolved_build_outputs = build_outputs.resolve()
    exec_globals = {'__builtins__': None}
    with cfg_path.open() as cfg_file:
        exec(cfg_file.read(), exec_globals) # pylint: disable=exec-used
    for file_spec in exec_globals['FILES']:
        # Only include files for official builds
        if 'official' not in file_spec['buildtype']:
            continue
        # If a file has an 'arch' field, it must have cpu_arch to be included
        if 'arch' in file_spec and cpu_arch not in file_spec['arch']:
            continue
        # From chrome/tools/build/make_zip.py, 'filename' is actually a glob pattern
        for file_path in resolved_build_outputs.glob(file_spec['filename']):
            # Do not package Windows debugging symbols
            if file_path.suffix.lower() == '.pdb':
                continue
            yield file_path.relative_to(resolved_build_outputs)


def _get_archive_writer(output_path):
    """
    Detects and returns the appropriate archive writer

    output_path is the pathlib.Path of the archive to write
    """
    if not output_path.suffixes:
        raise ValueError('Output name has no suffix: %s' % output_path.name)
    elif output_path.suffixes[-1].lower() == '.zip':
        import zipfile
        archive_root = Path(output_path.stem)
        output_archive = zipfile.ZipFile(str(output_path), 'w', zipfile.ZIP_DEFLATED)

        def add_func(in_path, arc_path):
            """Add files to zip archive"""
            if in_path.is_dir():
                for sub_path in in_path.rglob('*'):
                    output_archive.write(
                        str(sub_path), str(arc_path / sub_path.relative_to(in_path)))
            else:
                output_archive.write(str(in_path), str(arc_path))
    elif '.tar' in output_path.name.lower():
        import tarfile
        if len(output_path.suffixes) >= 2 and output_path.suffixes[-2].lower() == '.tar':
            tar_mode = 'w:%s' % output_path.suffixes[-1][1:]
            archive_root = Path(output_path.with_suffix('').stem)
        elif output_path.suffixes[-1].lower() == '.tar':
            tar_mode = 'w'
            archive_root = Path(output_path.stem)
        else:
            raise ValueError('Could not detect tar format for output: %s' % output_path.name)
        output_archive = tarfile.open(str(output_path), tar_mode)
        add_func = lambda in_path, arc_path: output_archive.add(str(in_path), str(arc_path))
    else:
        raise ValueError('Unknown archive extension with name: %s' % output_path.name)
    return output_archive, add_func, archive_root


def create_archive(file_iter, include_iter, build_outputs, output_path):
    """
    Create an archive of the build outputs. Supports zip and compressed tar archives.

    file_iter is an iterable of files to include in the zip archive.
    output_path is the pathlib.Path to write the new zip archive.
    build_outputs is a pathlib.Path to the build outputs
    """
    output_archive, add_func, archive_root = _get_archive_writer(output_path)
    with output_archive:
        for relative_path in file_iter:
            add_func(build_outputs / relative_path, archive_root / relative_path)
        for include_path in include_iter:
            add_func(include_path, archive_root / include_path.name)
