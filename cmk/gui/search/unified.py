#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.type_defs import SearchQuery

from .sorting import get_sorter
from .type_defs import (
    Provider,
    SearchEngine,
    SortType,
    UnifiedSearchResult,
    UnifiedSearchResultCounts,
    UnifiedSearchResultItem,
)


class UnifiedSearch:
    def __init__(
        self,
        *,
        setup_engine: SearchEngine,
        monitoring_engine: SearchEngine,
        customize_engine: SearchEngine,
    ) -> None:
        self._setup_engine = setup_engine
        self._monitoring_engine = monitoring_engine
        self._customize_engine = customize_engine

    def search(
        self,
        query: SearchQuery,
        *,
        provider: Provider | None = None,
        sort_type: SortType | None = None,
    ) -> UnifiedSearchResult:
        setup_results: list[UnifiedSearchResultItem] = []
        monitoring_results: list[UnifiedSearchResultItem] = []
        customize_results: list[UnifiedSearchResultItem] = []

        match provider:
            case "setup":
                setup_results.extend(self._setup_engine.search(query))
            case "monitoring":
                monitoring_results.extend(self._monitoring_engine.search(query))
            case "customize":
                customize_results.extend(self._customize_engine.search(query))
            case _:
                setup_results.extend(self._setup_engine.search(query))
                monitoring_results.extend(self._monitoring_engine.search(query))
                customize_results.extend(self._customize_engine.search(query))

        search_results = [*setup_results, *monitoring_results, *customize_results]
        get_sorter(sort_type, query)(search_results)

        result_counts = UnifiedSearchResultCounts(
            total=len(search_results),
            setup=len(setup_results),
            monitoring=len(monitoring_results),
            customize=len(customize_results),
        )

        return UnifiedSearchResult(results=search_results, counts=result_counts)
