#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import timedelta

from cmk.gui.cron import CronJob, CronJobRegistry
from cmk.gui.pages import PageRegistry
from cmk.gui.watolib.main_menu import MainModuleRegistry
from cmk.gui.watolib.mode import ModeRegistry

from . import _modes
from ._manager import execute_housekeeping_job


def register(
    page_registry: PageRegistry,
    mode_registry: ModeRegistry,
    main_module_registry: MainModuleRegistry,
    cron_job_registry: CronJobRegistry,
) -> None:
    cron_job_registry.register(
        CronJob(
            name="execute_housekeeping_job",
            callable=execute_housekeeping_job,
            interval=timedelta(minutes=1),
        )
    )
    _modes.register(page_registry, mode_registry, main_module_registry)
