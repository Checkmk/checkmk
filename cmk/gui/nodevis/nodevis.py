#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.cron import CronJobRegistry
from cmk.gui.nodevis import aggregation, topology
from cmk.gui.pages import PageRegistry
from cmk.gui.views.icon import IconRegistry
from cmk.gui.visuals.filter import FilterRegistry


def register(
    page_registry: PageRegistry,
    filter_registry: FilterRegistry,
    icon_and_action_registry: IconRegistry,
    cron_job_registry: CronJobRegistry,
) -> None:
    aggregation.register(page_registry, filter_registry, icon_and_action_registry)
    topology.register(page_registry, filter_registry, icon_and_action_registry, cron_job_registry)
