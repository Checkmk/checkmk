#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.background_job import BackgroundJobManager, job_registry
from cmk.gui.cron import register_job
from cmk.gui.log import logger


def housekeeping() -> None:
    housekeep_classes = list(job_registry.values())
    BackgroundJobManager(logger).do_housekeeping(housekeep_classes)


register_job(housekeeping)
