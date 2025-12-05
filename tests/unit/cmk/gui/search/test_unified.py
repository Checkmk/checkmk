#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import asdict

import pytest

from cmk.gui.search.unified import UnifiedSearch
from cmk.shared_typing.unified_search import (
    IconNames,
    ProviderName,
    UnifiedSearchResultItem,
    UnifiedSearchResultTarget,
)


class TestUnifiedSearch:
    @pytest.fixture(scope="class")
    def engine(self) -> UnifiedSearch:
        return UnifiedSearch(
            setup_engine=_FakeEngine(ProviderName.setup),
            monitoring_engine=_FakeEngine(ProviderName.monitoring),
            customize_engine=_FakeEngine(ProviderName.customize),
        )

    def test_match_with_all_providers(self, engine: UnifiedSearch) -> None:
        value = asdict(engine.search(query="host").counts)
        expected = {"total": 3, "setup": 1, "monitoring": 1, "customize": 1}
        assert value == expected

    def test_match_with_setup_provider(self, engine: UnifiedSearch) -> None:
        value = asdict(engine.search(query="host", provider=ProviderName.setup).counts)
        expected = {"total": 1, "setup": 1, "monitoring": 0, "customize": 0}
        assert value == expected

    def test_match_with_monitoring_provider(self, engine: UnifiedSearch) -> None:
        value = asdict(engine.search(query="host", provider=ProviderName.monitoring).counts)
        expected = {"total": 1, "setup": 0, "monitoring": 1, "customize": 0}
        assert value == expected

    def test_match_with_customize_provider(self, engine: UnifiedSearch) -> None:
        value = asdict(engine.search(query="host", provider=ProviderName.customize).counts)
        expected = {"total": 1, "setup": 0, "monitoring": 0, "customize": 1}
        assert value == expected

    def test_no_match_found(self, engine: UnifiedSearch) -> None:
        value = asdict(engine.search(query="this query gives no results").counts)
        expected = {"total": 0, "setup": 0, "monitoring": 0, "customize": 0}
        assert value == expected


class _FakeEngine:
    def __init__(self, provider: ProviderName) -> None:
        self._provider: ProviderName = provider
        self._results = _generate_fake_result_items(self._provider)

    def search(self, query: str) -> list[UnifiedSearchResultItem]:
        return [item for item in self._results if query in item.title]


def _generate_fake_result_items(
    provider: ProviderName,
) -> list[UnifiedSearchResultItem]:
    def build_item(title: str) -> UnifiedSearchResultItem:
        return UnifiedSearchResultItem(
            provider=provider,
            title=title,
            topic="",
            target=UnifiedSearchResultTarget(url=title),
            icon=IconNames.main_setup_active,
        )

    return [build_item(title) for title in ["hosts", "notifications", "users"]]
