#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import itertools
from collections.abc import Iterable

from cmk.gui.type_defs import SearchQuery, SearchResult, SearchResultsByTopic

from .engines.monitoring import SupportsMonitoringSearchEngine
from .engines.setup import SupportsSetupSearchEngine
from .sorting import get_sorter
from .type_defs import (
    Provider,
    SearchEngine,
    SortType,
    UnifiedSearchResult,
    UnifiedSearchResultCounts,
    UnifiedSearchResultItem,
)


# TODO: currently searching with legacy providers and then transforming the results into the desired
# unified search output. This is far from efficient, but is necessary to unblock the frontend
# development.
class UnifiedSearch:
    def __init__(
        self,
        *,
        setup_engine: SupportsSetupSearchEngine,
        monitoring_engine: SupportsMonitoringSearchEngine,
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
        setup_results_by_topic: SearchResultsByTopic = []
        monitoring_results_by_topic: SearchResultsByTopic = []
        customize_results: list[UnifiedSearchResultItem] = []

        match provider:
            case "setup":
                setup_results_by_topic = self._setup_engine.search(query)
            case "monitoring":
                monitoring_results_by_topic = self._monitoring_engine.search(query)
            case "customize":
                customize_results.extend(self._customize_engine.search(query))
            case _:
                setup_results_by_topic = self._setup_engine.search(query)
                monitoring_results_by_topic = self._monitoring_engine.search(query)
                customize_results.extend(self._customize_engine.search(query))

        setup_results = list(
            itertools.chain.from_iterable(
                self.transform_results(results, topic, provider="setup")
                for topic, results in setup_results_by_topic
            )
        )
        monitoring_results = list(
            itertools.chain.from_iterable(
                self.transform_results(results, topic, provider="monitoring")
                for topic, results in monitoring_results_by_topic
            )
        )
        search_results = [*setup_results, *monitoring_results, *customize_results]
        get_sorter(sort_type, query)(search_results)

        result_counts = UnifiedSearchResultCounts(
            total=len(search_results),
            setup=len(setup_results),
            monitoring=len(monitoring_results),
            customize=len(customize_results),
        )

        return UnifiedSearchResult(results=search_results, counts=result_counts)

    @staticmethod
    def transform_results(
        results: Iterable[SearchResult], topic: str, *, provider: Provider
    ) -> Iterable[UnifiedSearchResultItem]:
        return (
            UnifiedSearchResultItem(
                title=result.title,
                url=result.url,
                topic=topic,
                provider=provider,
                context=result.context,
            )
            for result in results
        )
