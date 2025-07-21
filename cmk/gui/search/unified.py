#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import itertools
from collections.abc import Iterable
from typing import cast, get_args, override

from cmk.gui.config import Config
from cmk.gui.http import request
from cmk.gui.pages import AjaxPage, PageResult
from cmk.gui.type_defs import (
    Provider,
    SearchQuery,
    SearchResult,
    SearchResultsByTopic,
    UnifiedSearchResult,
    UnifiedSearchResultCounts,
    UnifiedSearchResultItem,
)

from .engines.monitoring import MonitoringSearchEngine, SupportsMonitoringSearchEngine
from .engines.setup import SetupSearchEngine, SupportsSetupSearchEngine


# TODO: currently searching with legacy providers and then transforming the results into the desired
# unified search output. This is far from efficient, but is necessary to unblock the frontend
# development.
class UnifiedSearch:
    def __init__(
        self,
        setup_engine: SupportsSetupSearchEngine,
        monitoring_engine: SupportsMonitoringSearchEngine,
    ) -> None:
        self._setup_engine = setup_engine
        self._monitoring_engine = monitoring_engine

    def search(
        self, query: SearchQuery, provider: Provider | None, config: Config
    ) -> UnifiedSearchResult:
        setup_results_by_topic: SearchResultsByTopic = []
        monitoring_results_by_topic: SearchResultsByTopic = []

        match provider:
            case "setup":
                setup_results_by_topic = self._setup_engine.search(query, config)
            case "monitoring":
                monitoring_results_by_topic = self._monitoring_engine.search(query)
            case _:
                setup_results_by_topic = self._setup_engine.search(query, config)
                monitoring_results_by_topic = self._monitoring_engine.search(query)

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
        search_results = [*setup_results, *monitoring_results]

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


class PageUnifiedSearch(AjaxPage):
    @override
    def page(self, config: Config) -> PageResult:
        query = request.get_str_input_mandatory("q")
        provider = self._parse_provider_query_param()

        setup_engine = SetupSearchEngine()
        monitoring_engine = MonitoringSearchEngine()
        unified_search_engine = UnifiedSearch(setup_engine, monitoring_engine)

        response = unified_search_engine.search(query, provider, config)

        return {
            "url": request.url,
            "query": query,
            "counts": response.counts.serialize(),
            "results": [result.serialize() for result in response.results],
        }

    def _parse_provider_query_param(self) -> Provider | None:
        if (provider := request.get_str_input("provider")) is None:
            return None

        return cast(Provider, provider) if provider in get_args(Provider) else None
