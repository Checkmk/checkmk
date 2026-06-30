#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.shared_typing.unified_search import (
    ProviderName,
    SortType,
    UnifiedSearchResult,
    UnifiedSearchResultCounts,
    UnifiedSearchResultItem,
)

from .sorting import get_sorter
from .type_defs import IndexedEngine, SearchEngine


class UnifiedSearch:
    def __init__(
        self,
        *,
        indexed_engine: IndexedEngine,
        monitoring_engine: SearchEngine,
    ) -> None:
        self._indexed_engine = indexed_engine
        self._monitoring_engine = monitoring_engine

    def search(
        self,
        query: str,
        *,
        provider: ProviderName | None = None,
        sort_type: SortType | None = None,
    ) -> UnifiedSearchResult:
        setup_results: list[UnifiedSearchResultItem] = []
        monitoring_results: list[UnifiedSearchResultItem] = []
        customize_results: list[UnifiedSearchResultItem] = []

        match provider:
            case ProviderName.setup:
                setup_results = list(
                    self._indexed_engine.search(query, provider=ProviderName.setup)
                )
            case ProviderName.customize:
                customize_results = list(
                    self._indexed_engine.search(query, provider=ProviderName.customize)
                )
            case ProviderName.monitoring:
                monitoring_results.extend(self._monitoring_engine.search(query))
            case _:
                setup_results = list(
                    self._indexed_engine.search(query, provider=ProviderName.setup)
                )
                customize_results = list(
                    self._indexed_engine.search(query, provider=ProviderName.customize)
                )
                monitoring_results.extend(self._monitoring_engine.search(query))

        search_results = [*setup_results, *monitoring_results, *customize_results]
        get_sorter(sort_type, query)(search_results)

        result_counts = UnifiedSearchResultCounts(
            total=len(search_results),
            setup=len(setup_results),
            monitoring=len(monitoring_results),
            customize=len(customize_results),
        )

        return UnifiedSearchResult(results=search_results, counts=result_counts)
