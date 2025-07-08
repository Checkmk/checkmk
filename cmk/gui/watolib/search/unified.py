#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import itertools
from collections.abc import Iterable

from cmk.utils.redis import get_redis_client

from cmk.gui.config import Config
from cmk.gui.type_defs import (
    Provider,
    SearchQuery,
    SearchResult,
    SearchResultsByTopic,
    UnifiedSearchResult,
    UnifiedSearchResultCounts,
    UnifiedSearchResultItem,
)

from .engines.monitoring import QuicksearchManager
from .engines.setup import IndexSearcher, PermissionsHandler


# TODO: currently searching with legacy providers and then transforming the results into the desired
# unified search output. This is far from efficient, but is necessary to unblock the frontend
# development.
class UnifiedSearch:
    def __init__(self) -> None:
        self._setup_search = IndexSearcher(get_redis_client(), PermissionsHandler())
        self._monitoring_search = QuicksearchManager(raise_too_many_rows_error=False)

    def search(
        self, query: SearchQuery, provider: Provider | None, config: Config
    ) -> UnifiedSearchResult:
        setup_results_by_topic: SearchResultsByTopic = []
        monitoring_results_by_topic: SearchResultsByTopic = []

        match provider:
            case "setup":
                setup_results_by_topic = self._setup_search.search(query, config)
            case "monitoring":
                monitoring_results_by_topic = self._monitoring_search.generate_results(query)
            case _:
                setup_results_by_topic = self._setup_search.search(query, config)
                monitoring_results_by_topic = self._monitoring_search.generate_results(query)

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
        search_results = sorted(itertools.chain(setup_results, monitoring_results))

        result_counts = UnifiedSearchResultCounts(
            total=len(search_results),
            setup=len(setup_results),
            monitoring=len(monitoring_results),
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
