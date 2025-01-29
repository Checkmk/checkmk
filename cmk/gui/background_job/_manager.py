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

from cmk.gui import log

from ._base import BackgroundJob
from ._defines import BackgroundJobDefines
from ._registry import job_registry
from ._status import JobId, JobStatusSpec, JobStatusStates


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
                max_age = job_class.housekeeping_max_age_sec
                max_count = job_class.housekeeping_max_count
                all_jobs: list[tuple[str, JobStatusSpec]] = []

                job_instances = {}
                for job_id in job_ids:
                    job_instances[job_id] = BackgroundJob(job_id, logger=self._logger)
                    all_jobs.append((job_id, job_instances[job_id].get_status()))
                all_jobs.sort(key=lambda x: x[1].started, reverse=True)

                for entry in all_jobs[-1:0:-1]:
                    job_id, job_status = entry
                    if job_status.state == JobStatusStates.RUNNING:
                        continue

                    if len(all_jobs) > max_count or (time.time() - job_status.started > max_age):
                        job_instances[job_id].delete()
                        all_jobs.remove(entry)
        except Exception:
            self._logger.error(traceback.format_exc())


def execute_housekeeping_job() -> None:
    housekeep_classes = list(job_registry.values())
    BackgroundJobManager(log.logger).do_housekeeping(housekeep_classes)
