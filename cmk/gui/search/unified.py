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
from .type_defs import SearchEngine


class UnifiedSearch:
    def __init__(
        self,
        *,
        indexed_engine: SearchEngine,
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
                setup_results = [
                    item
                    for item in self._indexed_engine.search(query)
                    if item.provider == ProviderName.setup
                ]
            case ProviderName.customize:
                customize_results = [
                    item
                    for item in self._indexed_engine.search(query)
                    if item.provider == ProviderName.customize
                ]
            case ProviderName.monitoring:
                monitoring_results.extend(self._monitoring_engine.search(query))
            case _:
                for item in self._indexed_engine.search(query):
                    if item.provider == ProviderName.customize:
                        customize_results.append(item)
                    elif item.provider == ProviderName.setup:
                        setup_results.append(item)
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
