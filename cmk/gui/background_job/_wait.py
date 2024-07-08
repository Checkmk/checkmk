#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from contextlib import suppress
from logging import Logger

from pydantic import ValidationError

from ._base import BackgroundJob
from ._manager import BackgroundJobManager


def wait_for_background_jobs(logger: Logger, timeout: int) -> None:
    for job_id in running_job_ids(logger):
        job = BackgroundJob(job_id, logger=logger)
        logger.info("Waiting for %s to finish...", job_id)
        if not job.wait_for_completion(timeout):
            logger.warning("WARNING: Did not finish within %d seconds", timeout)


def running_job_ids(logger: Logger) -> list[str]:
    running = []
    for job_id in BackgroundJobManager(logger).get_all_job_ids():
        with suppress(SyntaxError, ValidationError):  # Ignore broken or incompatible job status
            if BackgroundJob(job_id, logger).is_active():
                running.append(job_id)
    return running
