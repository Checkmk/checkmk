#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from werkzeug.test import create_environ

from cmk.gui.http import Request
from cmk.gui.search._pages import _LIVESTATUS_ENGINE_ROW_LIMIT, PageUnifiedSearch
from cmk.shared_typing.unified_search import (
    MessageVariant,
    ProviderName,
    SortType,
    UnifiedSearchResultCounts,
)


def _request(query_string: str) -> Request:
    return Request(create_environ(query_string=query_string))


def _counts(monitoring: int) -> UnifiedSearchResultCounts:
    return UnifiedSearchResultCounts(total=monitoring, setup=0, monitoring=monitoring, customize=0)


@pytest.fixture(name="page")
def fixture_page() -> PageUnifiedSearch:
    return PageUnifiedSearch()


class TestParseProviderQueryParam:
    @pytest.mark.parametrize(
        "query_string, expected",
        [
            pytest.param("q=myhost&provider=setup", ProviderName.setup, id="setup"),
            pytest.param("q=myhost&provider=monitoring", ProviderName.monitoring, id="monitoring"),
            pytest.param("q=myhost&provider=customize", ProviderName.customize, id="customize"),
            pytest.param("q=myhost", None, id="no provider searches all of them"),
            pytest.param("q=myhost&provider=nonsense", None, id="unknown provider is ignored"),
            pytest.param("q=myhost&provider=", None, id="empty provider is ignored"),
        ],
    )
    def test_provider_is_parsed(
        self, page: PageUnifiedSearch, query_string: str, expected: ProviderName | None
    ) -> None:
        assert page._parse_provider_query_param(_request(query_string)) == expected


class TestParseSortQueryParam:
    @pytest.mark.parametrize(
        "query_string, expected",
        [
            pytest.param("q=myhost&sort=alphabetic", SortType.alphabetic, id="alphabetic"),
            pytest.param(
                "q=myhost&sort=weighted_index", SortType.weighted_index, id="weighted index"
            ),
            pytest.param("q=myhost", None, id="no sort keeps the engine order"),
            pytest.param("q=myhost&sort=nonsense", None, id="unknown sort is ignored"),
        ],
    )
    def test_sort_type_is_parsed(
        self, page: PageUnifiedSearch, query_string: str, expected: SortType | None
    ) -> None:
        assert page._parse_sort_query_param(_request(query_string)) == expected


class TestParseDisabledCollapser:
    @pytest.mark.parametrize(
        "query_string, expected",
        [
            pytest.param("q=myhost", True, id="collapsing is off without the parameter"),
            pytest.param("q=myhost&collapse=1", False, id="collapsing is on with the parameter"),
            pytest.param("q=myhost&collapse=0", False, id="any value switches collapsing on"),
        ],
    )
    def test_collapser_is_disabled_by_absence(
        self, page: PageUnifiedSearch, query_string: str, expected: bool
    ) -> None:
        assert page._parse_disabled_collapser(_request(query_string)) is expected


class TestCollectApiResponseMessages:
    def test_reaching_the_row_limit_is_reported_to_the_user(self, page: PageUnifiedSearch) -> None:
        messages = page._collect_api_response_messages(_counts(_LIVESTATUS_ENGINE_ROW_LIMIT))

        assert len(messages) == 1
        assert messages[0].message_variant is MessageVariant.info
        assert str(_LIVESTATUS_ENGINE_ROW_LIMIT) in (messages[0].header or "")

    @pytest.mark.parametrize(
        "monitoring",
        [
            pytest.param(0, id="no results"),
            pytest.param(_LIVESTATUS_ENGINE_ROW_LIMIT - 1, id="just below the row limit"),
        ],
    )
    def test_staying_below_the_row_limit_is_not_reported(
        self, page: PageUnifiedSearch, monitoring: int
    ) -> None:
        assert page._collect_api_response_messages(_counts(monitoring)) == []
