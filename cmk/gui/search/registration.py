#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui import hooks
from cmk.gui.background_job.job import BackgroundJobRegistry
from cmk.gui.pages import PageEndpoint, PageRegistry
from cmk.gui.watolib.host_match_item_generator import MatchItemGeneratorHosts
from cmk.gui.watolib.hosts_and_folders import collect_all_hosts
from cmk.gui.watolib.rule_match_item_generator import MatchItemGeneratorRules
from cmk.gui.watolib.rulespecs import rulespec_registry, RulespecGroupRegistry

from .engines.setup import launch_requests_processing_background, SearchIndexBackgroundJob
from .match_items import MatchItemGeneratorRegistry
from .pages import PageUnifiedSearch


def register(
    page_registry: PageRegistry,
    job_registry: BackgroundJobRegistry,
    match_item_generator_registry: MatchItemGeneratorRegistry,
    rulespec_group_registry: RulespecGroupRegistry,
) -> None:
    page_registry.register(PageEndpoint("ajax_unified_search", PageUnifiedSearch()))
    hooks.register_builtin("request-start", launch_requests_processing_background)
    job_registry.register(SearchIndexBackgroundJob)
    match_item_generator_registry.register(
        MatchItemGeneratorRules(
            "rules",
            rulespec_group_registry,
            rulespec_registry,
        )
    )
    match_item_generator_registry.register(
        MatchItemGeneratorHosts(
            "hosts",
            collect_all_hosts,
        )
    )
