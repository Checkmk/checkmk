#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import logging
import os
import time
import traceback
from collections.abc import Sequence
from typing import Final

from cmk.gui import log
from cmk.gui.config import Config

from ._base import BackgroundJob
from ._defines import BackgroundJobDefines
from ._registry import job_registry
from ._status import JobId, JobStatusStates


class BackgroundJobManager:
    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger.getChild("job_manager")
        super().__init__()

    def get_running_job_ids(self, job_class: type[BackgroundJob]) -> list[JobId]:
        """Checks for running jobs in the jobs default basedir"""
        all_jobs = self.get_all_job_ids(job_class)
        return [
            job_id for job_id in all_jobs if BackgroundJob(job_id, logger=self._logger).is_active()
        ]

    def get_all_job_ids(self, job_class: type[BackgroundJob] | None = None) -> list[JobId]:
        """Returns existing job directory names (aka Job IDs)

        Can optionally be called with a specific job class to get only job IDs related
        to that job."""
        if not os.path.exists(BackgroundJobDefines.base_dir):
            return []

        return [
            dirname
            for dirname in sorted(os.listdir(BackgroundJobDefines.base_dir))
            if os.path.isdir(os.path.join(BackgroundJobDefines.base_dir, dirname))
            and (job_class is None or dirname.startswith(job_class.job_prefix))
        ]

    def do_housekeeping(self, job_classes: Sequence[type[BackgroundJob]]) -> None:
        try:
            for job_class in job_classes:
                job_ids = self.get_all_job_ids(job_class)

                # We always keep at least one job (if present), so there is nothing to do in this
                # case. Also note that there is a race condition here: The file locking in
                # BackgroundJob.get_status creates the status file if it is missing. But when
                # starting a new job, we remove and re-create its working directory. The latter
                # operation can fail if the status file is re-created by the housekeeping job before
                # the removal is complete. Only jobs that re-use the same working directory every
                # time are prone to this (since there is nothing to remove otherwise). Such jobs are
                # excluded by the condition below.
                if len(job_ids) < 2:
                    continue

                max_age = job_class.housekeeping_max_age_sec
                max_count = job_class.housekeeping_max_count
                job_records_by_id = {
                    job_id: _HousekeepingJobRecord(job_id, self._logger) for job_id in job_ids
                }

                for job_record in sorted(
                    job_records_by_id.values(),
                    key=lambda job_record: job_record.status.started,
                )[:-1]:
                    if job_record.status.state in (
                        JobStatusStates.INITIALIZED,
                        JobStatusStates.RUNNING,
                    ):
                        continue

                    if len(job_records_by_id) > max_count or (
                        time.time() - job_record.status.started > max_age
                    ):
                        job_record.job.delete()
                        del job_records_by_id[job_record.job.get_job_id()]

        except Exception:
            self._logger.error(traceback.format_exc())


def execute_housekeeping_job(config: Config) -> None:
    housekeep_classes = list(job_registry.values())
    BackgroundJobManager(log.logger).do_housekeeping(housekeep_classes)


class _HousekeepingJobRecord:
    def __init__(self, job_id: JobId, logger: logging.Logger):
        self.job: Final = BackgroundJob(job_id, logger=logger)
        self.status: Final = self.job.get_status()
