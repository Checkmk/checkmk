#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
from functools import partial
from typing import Any

from cmk.ccc.plugin_registry import Registry


@dataclass
class CronJob:
    name: str
    # the callable should really return None, but some jobs return something (which is then ignored)
    callable: Callable[[], Any] | partial
    interval: timedelta


class CronJobRegistry(Registry[CronJob]):
    def plugin_name(self, instance: CronJob) -> str:
        return instance.name


cron_job_registry = CronJobRegistry()
