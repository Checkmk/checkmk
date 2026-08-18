#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from werkzeug.test import create_environ

from cmk.gui.config import Config
from cmk.gui.exceptions import MKUserError
from cmk.gui.http import Request
from cmk.gui.pages import PageContext, PageResult
from cmk.gui.search._pages import (
    _LIVESTATUS_ENGINE_ROW_LIMIT,
    _UNIFIED_SEARCH_LIVESTATUS_ORDER,
    PageUnifiedSearch,
)
from cmk.livestatus_client.testing import MockLiveStatusConnection
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


_HOST_ROWS = [
    {
        "name": "myhost",
        "host_name": "myhost",
        "alias": "My alias",
        "address": "10.10.15.20",
    }
]

_SERVICE_ROWS = [
    {
        "description": "CPU load",
        "host_name": "myhost",
        "service_description": "CPU load",
        "host_alias": "My alias",
        "host_address": "10.10.15.20",
    }
]


# The topic the "menu" filter of the search order reports its matches under. Those
# matches come from the live monitor menu, not from the fixtures below.
_MENU_TOPIC = "Monitor"

_LIVESTATUS_FILTER_QUERIES = {
    "h": ("hosts", "name"),
    "al": ("hosts", "alias"),
    "ad": ("hosts", "address"),
    "s": ("services", "service_description"),
}


def _expect_monitoring_queries(mock_livestatus: MockLiveStatusConnection, query: str) -> None:
    """One livestatus query per livestatus filter of the page's search order.

    The order is read from the production constant instead of being repeated here, so
    that changing it cannot silently invalidate these expectations. "menu" is answered
    from the monitor menu without touching livestatus; any other unknown filter raises
    a KeyError, which is the signal to extend the mapping above.
    """
    for filter_name, _behaviour in _UNIFIED_SEARCH_LIVESTATUS_ORDER:
        if filter_name == "menu":
            continue
        table, column = _LIVESTATUS_FILTER_QUERIES[filter_name]
        mock_livestatus.expect_query(
            f"GET {table}\nColumns: ...\nFilter: {column} ~~ {query}"
            f"\nLimit: {_LIVESTATUS_ENGINE_ROW_LIMIT + 1}\nColumnHeaders: off",
            match_type="ellipsis",
        )


def _monitored_hits(result: PageResult) -> list[tuple[str, str]]:
    """The (title, topic) pairs that came from livestatus.

    Monitor menu matches are filtered out: they depend on the real menu registry, so
    asserting on the full result list would break whenever a menu title happens to
    contain the search term.
    """
    assert isinstance(result, dict)
    return [
        (item["title"], item["topic"]) for item in result["results"] if item["topic"] != _MENU_TOPIC
    ]


@pytest.fixture(name="monitoring_sites")
def fixture_monitoring_sites(mock_livestatus: MockLiveStatusConnection) -> MockLiveStatusConnection:
    mock_livestatus.set_sites(["NO_SITE"])
    mock_livestatus.add_table("hosts", _HOST_ROWS, site="NO_SITE")
    mock_livestatus.add_table("services", _SERVICE_ROWS, site="NO_SITE")
    return mock_livestatus


@pytest.mark.usefixtures("allow_redis")
class TestPage:
    """The page builds both engines, so redis has to be reachable (fakeredis via
    allow_redis) even for a monitoring-only search, which never queries it."""

    @staticmethod
    def _context(config: Config, query_string: str) -> PageContext:
        return PageContext(
            config=config, request=Request(create_environ(query_string=query_string))
        )

    def test_a_monitoring_search_is_answered_as_an_api_response(
        self,
        page: PageUnifiedSearch,
        load_config: Config,
        monitoring_sites: MockLiveStatusConnection,
    ) -> None:
        _expect_monitoring_queries(monitoring_sites, "myhost")
        ctx = self._context(load_config, "q=myhost&provider=monitoring")

        with monitoring_sites(expect_status_query=True):
            result = page.page(ctx)

        assert isinstance(result, dict)
        assert result["query"] == "myhost"
        assert _monitored_hits(result) == [("myhost", "Host name")]
        assert result["counts"]["setup"] == 0
        assert result["counts"]["customize"] == 0
        assert result["counts"]["monitoring"] == len(result["results"])
        assert result["messages"] == []

    def test_the_host_alias_match_is_reported_under_its_own_topic(
        self,
        page: PageUnifiedSearch,
        load_config: Config,
        monitoring_sites: MockLiveStatusConnection,
    ) -> None:
        # "alias" matches the host alias only, so the result must not be presented as a
        # host name hit - the topic is what the frontend groups the results by.
        _expect_monitoring_queries(monitoring_sites, "alias")
        ctx = self._context(load_config, "q=alias&provider=monitoring")

        with monitoring_sites(expect_status_query=True):
            result = page.page(ctx)

        assert _monitored_hits(result) == [("My alias", "Host alias")]

    def test_a_query_without_matches_is_answered_with_empty_counts(
        self,
        page: PageUnifiedSearch,
        load_config: Config,
        monitoring_sites: MockLiveStatusConnection,
    ) -> None:
        _expect_monitoring_queries(monitoring_sites, "nonexistent")
        ctx = self._context(load_config, "q=nonexistent&provider=monitoring")

        with monitoring_sites(expect_status_query=True):
            result = page.page(ctx)

        assert _monitored_hits(result) == []

    def test_collapsing_merges_the_setup_and_monitoring_host_topics(
        self,
        page: PageUnifiedSearch,
        load_config: Config,
        monitoring_sites: MockLiveStatusConnection,
    ) -> None:
        # Without the collapse parameter the collapser is off, so every other case here
        # sees the raw "Host name" topic. With it on, a host hit is presented under the
        # "Hosts" topic even when there is no Setup counterpart to merge with.
        _expect_monitoring_queries(monitoring_sites, "myhost")
        ctx = self._context(load_config, "q=myhost&provider=monitoring&collapse=1")

        with monitoring_sites(expect_status_query=True):
            result = page.page(ctx)

        assert _monitored_hits(result) == [("myhost", "Hosts")]

    def test_a_missing_query_parameter_is_rejected(
        self, page: PageUnifiedSearch, load_config: Config
    ) -> None:
        with pytest.raises(MKUserError):
            page.page(self._context(load_config, "provider=monitoring"))
