#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui import hooks
from cmk.gui.background_job.job import BackgroundJobRegistry
from cmk.gui.pages import PageEndpoint, PageRegistry

from ._engines import _livestatus as livestatus_engine
from ._engines._redis import launch_requests_processing_background, SearchIndexBackgroundJob
from ._pages import PageUnifiedSearch
from .livestatus_links import MonitoringResultUrl
from .matchers import MatchPluginRegistry


def register(
    page_registry: PageRegistry,
    job_registry: BackgroundJobRegistry,
    match_plugin_registry: MatchPluginRegistry,
    monitoring_url: MonitoringResultUrl,
) -> None:
    page_registry.register(PageEndpoint("ajax_unified_search", PageUnifiedSearch(monitoring_url)))
    hooks.register_builtin("request-start", launch_requests_processing_background)
    job_registry.register(SearchIndexBackgroundJob)
    livestatus_engine.register(match_plugin_registry)
