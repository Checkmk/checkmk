#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable

from ..type_defs import UnifiedSearchResultItem


class CustomizeSearchEngine:
    def __init__(self) -> None:
        # TODO: we are currently only supporting searching over the pages that are present in the
        # Customize menu. For simplicity, we'll just read from this hardcoded store, but will want
        # to migrate to a more robust cache when improving customize search capability.
        self._result_store = (
            ("General", "Topics", "pagetype_topics.py"),
            ("General", "Custom sidebar elements", "custom_snapins.py"),
            ("General", "Bookmark lists", "bookmark_lists.py"),
            ("Visualization", "Views", "edit_views.py"),
            ("Visualization", "Dashboards", "edit_dashboards.py"),
            ("Graphs", "Forecast graphs", "forecast_graphs.py"),
            ("Graphs", "Custom graphs", "custom_graphs.py"),
            ("Graphs", "Graph collections graphs", "graph_collections.py"),
            ("Graphs", "Graph tunings", "graph_tunings.py"),
            ("Business reporting", "Reports", "edit_reports.py"),
            ("Business reporting", "Service Level Agreements", "sla_configurations.py"),
        )

    def search(self, query: str) -> Iterable[UnifiedSearchResultItem]:
        return (
            UnifiedSearchResultItem(provider="customize", title=title, topic=topic, url=url)
            for topic, title, url in self._result_store
            if query.lower() in title.lower()
        )
