#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from logging import Logger
from typing import override

from cmk.gui.watolib.sites import SitesConfigFile

from cmk.update_config.registry import update_action_registry, UpdateAction


class WriteSitesMk(UpdateAction):
    """Make sure the site configuration is written to disk so that 2.5 can read from it.

    Single site setups might have never edited their site configurations, so
    sites.mk might not exist. 2.5 removed the fallback to default values, which
    in this case would lead to validation errors in rulesets that depend on site
    configuration values in the PRE update step (like automatic agent
    registration with a SetupSiteChoices valuespec).

    This only catches an edge case since 2.5 comes with an update step itself
    that would write sites.mk, but PRE update actions are executed before that
    and run with the configuration present before updating.
    """

    @override
    def __call__(self, logger: Logger) -> None:
        store = SitesConfigFile()
        connection_configs = store.load_for_reading()
        store.save(connection_configs)


update_action_registry.register(
    WriteSitesMk(
        name="write_sites_mk",
        title="Make sure sites.mk exists",
        sort_index=120,  # can run whenever
    )
)
