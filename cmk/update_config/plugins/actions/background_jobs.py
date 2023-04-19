#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import shutil
from collections.abc import Iterator
from logging import Logger
from pathlib import Path
from typing import Any

from cmk.utils.log import VERBOSE

from cmk.gui.background_job import (
    BackgroundJobDefines,
    BackgroundJobManager,
    job_registry,
    JobId,
    JobStatusSpec,
    JobStatusStates,
    JobStatusStore,
)

from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.update_config.update_state import UpdateActionState


class UpdateBackgroundJobStatusSpec(UpdateAction):
    def __call__(self, logger: Logger, update_action_state: UpdateActionState) -> None:
        for job_id in _get_all_job_ids(logger):
            update_job_status(logger, Path(BackgroundJobDefines.base_dir, job_id))


def update_job_status(logger: Logger, job_path: Path) -> None:
    logger.log(VERBOSE, "Processing job status from %s", job_path)
    job_status_store = JobStatusStore(str(job_path))
    try:
        raw_status = job_status_store.read_raw()
    except ValueError:
        raw_status = None  # Don't fail on falsy values here

    if not raw_status:
        # The file either vanished magically, was empty or contained None or an empty dict
        # for some weird reason. Instead of trying to recover this, we clean up this job.
        logger.log(VERBOSE, "Removing unreadable job status")
        shutil.rmtree(job_path)
        return

    raw_status = migrate_job_status_spec(
        raw_status, jobstatus_ctime=job_status_store._jobstatus_path.stat().st_ctime
    )

    job_status_store.write(JobStatusSpec.parse_obj(raw_status))


def _get_all_job_ids(logger: Logger) -> Iterator[JobId]:
    manager = BackgroundJobManager(logger)
    for job_class in list(job_registry.values()):
        yield from manager.get_all_job_ids(job_class)


def migrate_job_status_spec(status: dict[str, Any], jobstatus_ctime: float) -> dict[str, Any]:
    """Apply actions to make the existing data structures compatible with the current JobStatusSpec
    data structure"""
    status = status.copy()
    if "state" not in status:
        status["state"] = JobStatusStates.INITIALIZED
        status["started"] = jobstatus_ctime

    status.setdefault("pid", None)

    loginfo = status.setdefault(
        "loginfo",
        {
            "JobProgressUpdate": [],
            "JobResult": [],
            "JobException": [],
        },
    )
    loginfo.setdefault("JobProgressUpdate", [])
    loginfo.setdefault("JobResult", [])
    loginfo.setdefault("JobException", [])

    map_job_state_to_is_active = {
        JobStatusStates.INITIALIZED: True,
        JobStatusStates.RUNNING: True,
        JobStatusStates.FINISHED: False,
        JobStatusStates.STOPPED: False,
        JobStatusStates.EXCEPTION: False,
    }
    status["is_active"] = map_job_state_to_is_active[status["state"]]

    return status


update_action_registry.register(
    UpdateBackgroundJobStatusSpec(
        name="background_job_status_specs",
        title="Background jobs",
        sort_index=60,
    )
)
