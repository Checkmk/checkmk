#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from typing import override

from cmk.gui import job_scheduler
from cmk.update_config.registry import update_action_registry, UpdateAction


class ResetDeprecationsScheduling(UpdateAction):  # pylint: disable=too-few-public-methods
    @override
    def __call__(self, logger: Logger) -> None:
        # Note: We have to call 'reset_scheduling' from 'job_scheduler' directly and NOT via
        # fast API '/reset_scheduling' because the job-scheduler is not yet running during
        # cmk-update-config.
        job_scheduler.reset_scheduling("execute_deprecation_tests_and_notify_users")


update_action_registry.register(
    ResetDeprecationsScheduling(
        name="reset_deprecations_scheduling",
        title="Reset deprecations scheduling",
        sort_index=200,
    )
)
