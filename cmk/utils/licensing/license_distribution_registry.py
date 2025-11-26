#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Collection
from logging import Logger

from cmk.utils.automation_config import RemoteAutomationConfig


class LicenseDistributionRegistry:
    def __init__(self) -> None:
        self.distribution_function: (
            Callable[[Logger, Collection[RemoteAutomationConfig]], None] | None
        ) = None

    def register(
        self, distribution_function: Callable[[Logger, Collection[RemoteAutomationConfig]], None]
    ) -> None:
        self.distribution_function = distribution_function


license_distribution_registry = LicenseDistributionRegistry()


def distribute_license_to_remotes(
    logger: Logger, remote_automation_configs: Collection[RemoteAutomationConfig]
) -> None:
    if license_distribution_registry.distribution_function is not None:
        license_distribution_registry.distribution_function(logger, remote_automation_configs)
