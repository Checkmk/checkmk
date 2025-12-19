#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable

from cmk.gui.search.legacy_helpers import transform_legacy_loading_transition_to_unified
from cmk.shared_typing.unified_search import (
    LoadingTransition,
    ProviderName,
    UnifiedSearchResultItem,
    UnifiedSearchResultTarget,
)


class CustomizeSearchEngine:
    def __init__(self) -> None:
        # TODO: we are currently only supporting searching over the pages that are present in the
        # Customize menu. For simplicity, we'll just read from this hardcoded store, but will want
        # to migrate to a more robust cache when improving customize search capability.
        self._result_store = (
            ("General", "Topics", "pagetype_topics.py", LoadingTransition.table),
            ("General", "Custom sidebar elements", "custom_snapins.py", LoadingTransition.table),
            ("General", "Bookmark lists", "bookmark_lists.py", LoadingTransition.table),
            ("Visualization", "Views", "edit_views.py", LoadingTransition.dashboard),
            ("Visualization", "Dashboards", "edit_dashboards.py", LoadingTransition.dashboard),
            ("Graphs", "Forecast graphs", "forecast_graphs.py", LoadingTransition.dashboard),
            ("Graphs", "Custom graphs", "custom_graphs.py", LoadingTransition.dashboard),
            (
                "Graphs",
                "Graph collections graphs",
                "graph_collections.py",
                LoadingTransition.dashboard,
            ),
            ("Graphs", "Graph tunings", "graph_tunings.py", LoadingTransition.dashboard),
            ("Business reporting", "Reports", "edit_reports.py", LoadingTransition.table),
            (
                "Business reporting",
                "Service Level Agreements",
                "sla_configurations.py",
                LoadingTransition.table,
            ),
        )

    def search(self, query: str) -> Iterable[UnifiedSearchResultItem]:
        return (
            UnifiedSearchResultItem(
                provider=ProviderName.customize,
                title=title,
                topic=topic,
                target=UnifiedSearchResultTarget(
                    url=url,
                    transition=transform_legacy_loading_transition_to_unified(
                        loading_transition.value
                    )
                    if loading_transition
                    else None,
                ),
            )
            for topic, title, url, loading_transition in self._result_store
            if query.lower() in title.lower()
        )
