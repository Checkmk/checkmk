#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from pathlib import Path
from typing import Any, TypedDict

from cmk.ccc import store

from cmk.gui.i18n import _

from ._defines import BackgroundJobDefines
from ._status import JobLogInfo, JobStatusSpec, JobStatusStates


# Same as JobStatusSpec but without mandatory attributes. Is there a way to prevent the duplication?
class JobStatusSpecUpdate(TypedDict, total=False):
    state: str  # Make Literal["initialized", "running", "finished", "stopped", "exception"]
    started: float  # Change to Timestamp type later
    pid: int | None
    loginfo: JobLogInfo
    is_active: bool
    duration: float  # Make this mandatory
    title: str
    stoppable: bool
    deletable: bool
    user: str | None
    estimated_duration: float | None
    ppid: int
    logfile_path: str
    acknowledged_by: str | None
    lock_wato: bool
    # Only used by ServiceDiscoveryBackgroundJob
    host_name: str


class JobStatusStore:
    def __init__(self, work_dir: str) -> None:
        super().__init__()
        self._work_dir = work_dir
        self._jobstatus_path = Path(work_dir) / BackgroundJobDefines.jobstatus_filename

        self._progress_update_path = Path(work_dir) / BackgroundJobDefines.progress_update_filename
        self._result_message_path = Path(work_dir) / BackgroundJobDefines.result_message_filename
        self._exceptions_path = Path(work_dir) / BackgroundJobDefines.exceptions_filename

    def read(self) -> JobStatusSpec:
        initialized = JobStatusSpec(
            state=JobStatusStates.INITIALIZED,
            started=time.time(),
            pid=None,
            is_active=False,
            loginfo={
                "JobProgressUpdate": [
                    _(
                        "Waiting for first status update from the job. In case "
                        "this message is shown for a longer time, the startup "
                        "got interrupted."
                    )
                ],
                "JobResult": [],
                "JobException": [],
            },
        )

        if not self._jobstatus_path.exists():
            return initialized

        initialized.started = self._jobstatus_path.stat().st_mtime

        if not (raw_status_spec := self.read_raw()):
            # Job status file might have just been created during locking. In this
            # case the file does not have any content yet and falls back to the default
            # value, which is an empty dict.
            return initialized

        try:
            data: JobStatusSpec = JobStatusSpec.model_validate(raw_status_spec)
        finally:
            store.release_lock(str(self._jobstatus_path))

        def _log_lines(path: Path) -> list[str]:
            try:
                with path.open(encoding="utf-8") as f:
                    return f.read().splitlines()
            except FileNotFoundError:
                return []

        data.loginfo["JobProgressUpdate"] = _log_lines(self._progress_update_path)
        data.loginfo["JobResult"] = _log_lines(self._result_message_path)
        data.loginfo["JobException"] = _log_lines(self._exceptions_path)

        return data

    def read_raw(self) -> dict[str, Any]:
        status: dict[str, Any] = store.load_object_from_file(
            self._jobstatus_path, default={}, lock=True
        )
        return status

    def exists(self) -> bool:
        return self._jobstatus_path.exists()

    def write(self, status: JobStatusSpec) -> None:
        store.save_object_to_file(self._jobstatus_path, status.model_dump())

    def update(self, params: JobStatusSpecUpdate) -> None:
        if not self._jobstatus_path.parent.exists():
            return

        if params:
            try:
                self.write(JobStatusSpec.model_validate({**self.read_raw(), **params}))
            finally:
                store.release_lock(str(self._jobstatus_path))
