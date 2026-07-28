# -*- coding: UTF-8 -*-

# Copyright (c) 2026 The ungoogled-chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Regression tests for disable-gcm PushManager.subscribe() fail-fast."""

import logging
import subprocess
import tempfile
from pathlib import Path

ENCODING = 'UTF-8'
PATCH_REL = 'core/ungoogled-chromium/disable-gcm.patch'
ENSURE_STARTED_FIXTURE = """}

GCMClient::Result GCMDriverDesktop::EnsureStarted(
    GCMClient::StartMode start_mode) {
  DCHECK(ui_thread_->RunsTasksInCurrentSequence());

  if (gcm_started_)
    return GCMClient::SUCCESS;

  // Have any app requested the service?
  if (app_handlers().empty())
    return GCMClient::UNKNOWN_ERROR;

  if (!delayed_task_controller_)
    delayed_task_controller_ = std::make_unique<GCMDelayedTaskController>();

  // Note that we need to pass weak pointer again since the existing weak
  // pointer in IOWorker might have been invalidated when GCM is stopped.
  io_thread_->PostTask(
      FROM_HERE, base::BindOnce(&GCMDriverDesktop::IOWorker::Start,
                                base::Unretained(io_worker_.get()), start_mode,
                                weak_ptr_factory_.GetWeakPtr(),
                                /*time_task_posted=*/base::TimeTicks::Now()));

  return GCMClient::SUCCESS;
}

void GCMDriverDesktop::RemoveCachedData() {
}
"""


def _series_entries(series_path):
    return [
        line.strip() for line in series_path.read_text(encoding=ENCODING).splitlines()
        if line.strip() and not line.strip().startswith('#')
    ]


def _desktop_hunk_text(patch_content):
    marker = '--- a/components/gcm_driver/gcm_driver_desktop.cc\n'
    assert marker in patch_content
    hunk = marker + patch_content.split(marker, 1)[1]
    lines = []
    for line in hunk.splitlines(keepends=True):
        if line.startswith('@@'):
            lines.append('@@ -1,28 +1,10 @@\n')
        else:
            lines.append(line)
    return ''.join(lines)


def _run_patch(args, cwd):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=False)


def _assert_patch_content(patch_path):
    patch_content = patch_path.read_text(encoding=ENCODING)
    assert 'GCMDriverDesktop::EnsureStarted' in patch_content
    assert patch_content.count('+  return GCMClient::GCM_DISABLED;') == 1
    assert 'void GCMClientImpl::Start(StartMode start_mode)' in patch_content
    return patch_content


def _assert_ensure_started_applies(patch_content):
    with tempfile.TemporaryDirectory() as tmpdirname:
        root = Path(tmpdirname)
        target = root / 'components/gcm_driver/gcm_driver_desktop.cc'
        target.parent.mkdir(parents=True)
        target.write_text(ENSURE_STARTED_FIXTURE, encoding=ENCODING)

        local_patch = root / 'test.patch'
        local_patch.write_text(_desktop_hunk_text(patch_content), encoding=ENCODING)

        dry = _run_patch(['patch', '-p1', '--dry-run', '-i', str(local_patch)], root)
        assert dry.returncode == 0, dry.stdout + dry.stderr

        applied = _run_patch(['patch', '-p1', '-i', str(local_patch)], root)
        assert applied.returncode == 0, applied.stdout + applied.stderr
        patched = target.read_text(encoding=ENCODING)
        assert 'return GCMClient::GCM_DISABLED;' in patched
        assert 'delayed_task_controller_ = std::make_unique' not in patched


def test_disable_gcm_fail_fast_push():
    """Ensure disable-gcm fails PushManager.subscribe() instead of hanging."""

    logging.basicConfig(level=logging.DEBUG)
    log = logging.getLogger('ungoogled')

    patches_dir = Path(__file__).resolve().parents[2] / 'patches'
    series_path = patches_dir / 'series'
    patch_path = patches_dir / PATCH_REL

    log.info('Check series includes disable-gcm')
    assert PATCH_REL in _series_entries(series_path)

    log.info('Check patch returns GCM_DISABLED from EnsureStarted')
    patch_content = _assert_patch_content(patch_path)

    log.info('Check EnsureStarted hunk applies')
    _assert_ensure_started_applies(patch_content)


if __name__ == '__main__':
    test_disable_gcm_fail_fast_push()
