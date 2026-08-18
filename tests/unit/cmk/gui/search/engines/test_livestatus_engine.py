#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import override
from urllib.parse import parse_qsl, urlsplit

import pytest
from werkzeug.test import create_environ

from cmk.gui.config import Config
from cmk.gui.http import Request
from cmk.gui.permissions import permission_registry
from cmk.gui.search._engines._livestatus import (
    ABCQuicksearchConductor,
    BasicPluginQuicksearchConductor,
    FilterBehaviour,
    get_url_builder,
    GroupMatchPlugin,
    HostMatchPlugin,
    LivestatusQuicksearchConductor,
    LivestatusResult,
    LivestatusSearchEngine,
    QuicksearchManager,
    UrlBuilder,
    UsedFilters,
)
from cmk.gui.type_defs import HTTPVariables, SearchResult
from cmk.gui.utils.roles import UserPermissions
from cmk.livestatus_client.testing import MockLiveStatusConnection
from cmk.shared_typing.unified_search import ProviderName


def _build_url(query_string: str = "q=myhost") -> UrlBuilder:
    return get_url_builder(Request(create_environ(query_string=query_string)))


def _url_params(url: str) -> dict[str, str]:
    return dict(parse_qsl(urlsplit(url).query))


class TestGetSearchUrlParams:
    """The "press Enter" search path (search_open.py) builds its target URL via
    get_search_url_params(). For an exact host match it must carry the matched
    site, otherwise context-dependent page menu entries (e.g. the host inventory)
    are suppressed - see cmk.gui.views.visual_type._compute_link_from_result()."""

    def test_exact_host_match_includes_site(self) -> None:
        conductor = LivestatusQuicksearchConductor(
            {"h": ["myhost"]}, FilterBehaviour.CONTINUE, row_limit=80
        )
        conductor._livestatus_table = "hosts"
        conductor._rows = [{"site": "mysite", "name": "myhost", "host_name": "myhost"}]
        conductor._used_search_plugins = [HostMatchPlugin(livestatus_field="name", name="h")]

        url_params = conductor.get_search_url_params()

        assert ("view_name", "host") in url_params
        assert ("host", "myhost") in url_params
        assert ("site", "mysite") in url_params

    def test_multiple_host_matches_omit_site(self) -> None:
        # Same host name present on two sites -> not an exact match. We navigate to
        # the search view listing both, so no single site may be pinned.
        conductor = LivestatusQuicksearchConductor(
            {"h": ["myhost"]}, FilterBehaviour.CONTINUE, row_limit=80
        )
        conductor._livestatus_table = "hosts"
        conductor._rows = [
            {"site": "site1", "name": "myhost", "host_name": "myhost"},
            {"site": "site2", "name": "myhost", "host_name": "myhost"},
        ]
        conductor._used_search_plugins = [HostMatchPlugin(livestatus_field="name", name="h")]

        url_params = conductor.get_search_url_params()

        assert ("view_name", "searchhost") in url_params
        assert not any(key == "site" for key, _value in url_params)

    def test_group_match_omits_site(self) -> None:
        conductor = LivestatusQuicksearchConductor(
            {"hg": ["mygroup"]}, FilterBehaviour.CONTINUE, row_limit=80
        )
        conductor._livestatus_table = "hostgroups"
        conductor._rows = [{"site": "mysite", "name": "mygroup"}]
        conductor._used_search_plugins = [GroupMatchPlugin(group_type="host", name="hg")]

        url_params = conductor.get_search_url_params()

        assert not any(key == "site" for key, _value in url_params)

    def test_a_filter_the_target_view_does_not_know_is_skipped(self) -> None:
        # "hg" has no url variables for the single host view, so it must not contribute
        # anything - otherwise the view is filtered by a variable it cannot interpret.
        # The table and the plugin list are derived the way production does it, because
        # a hand-picked combination is easily one the engine can never build.
        conductor = LivestatusQuicksearchConductor(
            {"h": ["myhost"], "hg": ["mygroup"]}, FilterBehaviour.CONTINUE, row_limit=80
        )
        conductor._determine_livestatus_table()
        conductor._used_search_plugins = conductor._get_used_search_plugins()
        conductor._rows = [
            {"site": "mysite", "name": "myhost", "host_name": "myhost", "host_groups": ["mygroup"]}
        ]

        url_params = conductor.get_search_url_params()

        assert conductor.livestatus_table == "hosts"
        assert {plugin.name for plugin in conductor._used_search_plugins} == {"h", "hg"}
        assert ("view_name", "host") in url_params
        assert ("host", "myhost") in url_params
        assert not any("group" in key for key, _value in url_params)


class TestIsInvalidRegex:
    @pytest.mark.parametrize(
        "query",
        [
            pytest.param("*heute", id="leading glob wildcard"),
            pytest.param("*", id="glob wildcard only"),
            pytest.param("heu*te", id="glob wildcard in the middle"),
        ],
    )
    def test_glob_query_is_not_rejected_before_it_gets_sanitized(self, query: str) -> None:
        assert LivestatusSearchEngine._is_invalid_regex(query) is False

    @pytest.mark.parametrize(
        "query",
        [
            pytest.param("(heute", id="unterminated group"),
            pytest.param("+heute", id="nothing to repeat"),
            pytest.param("heute[", id="unterminated character set"),
        ],
    )
    def test_broken_regex_is_rejected(self, query: str) -> None:
        assert LivestatusSearchEngine._is_invalid_regex(query) is True


class TestFindSearchObjectExpressions:
    @pytest.mark.parametrize(
        "query, expected",
        [
            pytest.param("h:myhost", [("h:", 0)], id="single filter"),
            pytest.param("h:myhost s:CPU", [("h:", 0), (" s:", 8)], id="two filters"),
            pytest.param("hg:mygroup", [("hg:", 0)], id="two letter filter"),
            pytest.param("myhost", [], id="plain query"),
            pytest.param("", [], id="empty query"),
            pytest.param("https://myhost", [], id="url is not read as a service filter"),
            pytest.param("Filesystem /var", [], id="path is not read as a filter"),
        ],
    )
    def test_expressions_are_extracted(self, query: str, expected: list[tuple[str, int]]) -> None:
        assert QuicksearchManager._find_search_object_expressions(query) == expected


class TestGetUsedFiltersFromQuery:
    @staticmethod
    def _used_filters(query: str) -> UsedFilters:
        return QuicksearchManager._get_used_filters_from_query(
            query, QuicksearchManager._find_search_object_expressions(query)
        )

    @pytest.mark.parametrize(
        "query, expected",
        [
            pytest.param("h:myhost", {"h": ["myhost"]}, id="single filter"),
            pytest.param(
                "h:myhost s:CPU", {"h": ["myhost"], "s": ["CPU"]}, id="one filter per plugin"
            ),
            pytest.param("h: myhost ", {"h": ["myhost"]}, id="surrounding whitespace is stripped"),
            pytest.param("h:my*host", {"h": ["my.*host"]}, id="glob is converted to regex"),
            pytest.param(
                "h:one h:two", {"h": ["two", "one"]}, id="repeated filter is collected backwards"
            ),
        ],
    )
    def test_filter_texts_are_extracted(self, query: str, expected: UsedFilters) -> None:
        assert self._used_filters(query) == expected


class TestDetermineLivestatusTable:
    @pytest.mark.parametrize(
        "used_filters, expected",
        [
            pytest.param({"h": ["myhost"]}, "hosts", id="host name"),
            pytest.param({"al": ["myalias"]}, "hosts", id="host alias"),
            pytest.param({"s": ["CPU"]}, "services", id="service"),
            pytest.param({"st": ["ok"]}, "services", id="service state"),
            pytest.param({"hg": ["mygroup"]}, "hostgroups", id="host group"),
            pytest.param({"sg": ["mygroup"]}, "servicegroups", id="service group"),
            pytest.param({"h": ["myhost"], "s": ["CPU"]}, "services", id="host and service"),
            pytest.param(
                {"sg": ["mygroup"], "h": ["myhost"]},
                "services",
                id="service group narrowed by host",
            ),
            pytest.param(
                {"sg": ["mygroup"], "hg": ["mygroup"]},
                "services",
                id="service group narrowed by host group",
            ),
        ],
    )
    def test_table_is_chosen_by_filter_precedence(
        self, used_filters: UsedFilters, expected: str
    ) -> None:
        conductor = LivestatusQuicksearchConductor(
            used_filters, FilterBehaviour.CONTINUE, row_limit=80
        )

        conductor._determine_livestatus_table()

        assert conductor.livestatus_table == expected


class TestGetTargetView:
    @pytest.mark.parametrize(
        "livestatus_table, expected",
        [
            pytest.param("hosts", "host", id="hosts"),
            pytest.param("services", "allservices", id="services"),
            pytest.param("hostgroups", "hostgroup", id="host groups"),
            pytest.param("servicegroups", "servicegroup", id="service groups"),
        ],
    )
    def test_exact_match_opens_the_single_object_view(
        self, livestatus_table: str, expected: str
    ) -> None:
        conductor = LivestatusQuicksearchConductor(
            {"h": ["myhost"]}, FilterBehaviour.CONTINUE, row_limit=80
        )
        conductor._livestatus_table = livestatus_table

        assert conductor._get_target_view(exact_match=True) == expected

    @pytest.mark.parametrize(
        "livestatus_table, expected",
        [
            pytest.param("hosts", "searchhost", id="hosts"),
            pytest.param("services", "searchsvc", id="services"),
            pytest.param("hostgroups", "hostgroups", id="host groups"),
            pytest.param("servicegroups", "svcgroups", id="service groups"),
        ],
    )
    def test_multiple_matches_open_the_search_view(
        self, livestatus_table: str, expected: str
    ) -> None:
        conductor = LivestatusQuicksearchConductor(
            {"h": ["myhost"]}, FilterBehaviour.CONTINUE, row_limit=80
        )
        conductor._livestatus_table = livestatus_table

        assert conductor._get_target_view(exact_match=False) == expected

    def test_unknown_table_has_no_target_view(self) -> None:
        conductor = LivestatusQuicksearchConductor(
            {"h": ["myhost"]}, FilterBehaviour.CONTINUE, row_limit=80
        )
        conductor._livestatus_table = ""

        with pytest.raises(NotImplementedError):
            conductor._get_target_view()


class TestGenerateDisplayTexts:
    @staticmethod
    def _conductor(
        livestatus_table: str, used_filters: UsedFilters | None = None
    ) -> LivestatusQuicksearchConductor:
        conductor = LivestatusQuicksearchConductor(
            used_filters or {"h": ["myhost"]}, FilterBehaviour.CONTINUE, row_limit=80
        )
        conductor._livestatus_table = livestatus_table
        return conductor

    def test_service_titles_are_taken_from_the_description(self) -> None:
        conductor = self._conductor("services")
        elements = [
            LivestatusResult(
                text_tokens=[("s", "CPU load")],
                url="view.py?a=1",
                row={"description": "CPU load", "host_name": "myhost"},
                display_text="",
            )
        ]

        results = conductor._generate_display_texts(elements)

        assert [(result.title, result.url, result.context) for result in results] == [
            ("CPU load", "view.py?a=1", "")
        ]

    def test_ambiguous_host_titles_are_disambiguated_by_the_host_name(self) -> None:
        conductor = self._conductor("hosts")
        elements = [
            LivestatusResult(
                text_tokens=[("h", "myhost")],
                url="view.py?a=1",
                row={"name": "myhost", "site": "site1"},
                display_text="",
            ),
            LivestatusResult(
                text_tokens=[("h", "myhost")],
                url="view.py?a=2",
                row={"name": "myhost", "site": "site2"},
                display_text="",
            ),
        ]

        results = conductor._generate_display_texts(elements)

        assert [(result.url, result.context) for result in results] == [
            ("view.py?a=1&host_regex=myhost", "myhost"),
            ("view.py?a=2&host_regex=myhost", "myhost"),
        ]

    def test_ambiguous_host_titles_prefer_the_alias_as_context(self) -> None:
        conductor = self._conductor("hosts")
        elements = [
            LivestatusResult(
                text_tokens=[("h", "myhost"), ("al", "My alias")],
                url="view.py?a=1",
                row={"name": "myhost", "site": "site1"},
                display_text="",
            ),
            LivestatusResult(
                text_tokens=[("h", "myhost"), ("al", "Another alias")],
                url="view.py?a=2",
                row={"name": "myhost", "site": "site2"},
                display_text="",
            ),
        ]

        results = conductor._generate_display_texts(elements)

        assert [result.context for result in results] == ["My alias", "Another alias"]

    def test_unique_host_addresses_show_the_host_name_as_context(self) -> None:
        conductor = self._conductor("hosts", {"ad": ["10.10.15.20"]})
        elements = [
            LivestatusResult(
                text_tokens=[("ad", "10.10.15.200")],
                url="view.py?a=1",
                row={"name": "myhost", "site": "site1"},
                display_text="",
            ),
            LivestatusResult(
                text_tokens=[("ad", "10.10.15.201")],
                url="view.py?a=2",
                row={"name": "otherhost", "site": "site1"},
                display_text="",
            ),
        ]

        results = conductor._generate_display_texts(elements)

        assert [(result.title, result.url, result.context) for result in results] == [
            ("10.10.15.200", "view.py?a=1", "myhost"),
            ("10.10.15.201", "view.py?a=2", "otherhost"),
        ]

    def test_address_match_titled_by_another_filter_gets_no_context(self) -> None:
        conductor = self._conductor("hosts", {"al": ["My alias"], "ad": ["10.10.15.20"]})
        elements = [
            LivestatusResult(
                text_tokens=[("al", "My alias"), ("ad", "10.10.15.200")],
                url="view.py?a=1",
                row={"name": "myhost", "site": "site1"},
                display_text="",
            )
        ]

        results = conductor._generate_display_texts(elements)

        assert [(result.title, result.context) for result in results] == [("My alias", "")]

    def test_host_named_after_its_address_gets_no_redundant_context(self) -> None:
        conductor = self._conductor("hosts", {"ad": ["10.10.15.20"]})
        elements = [
            LivestatusResult(
                text_tokens=[("ad", "10.10.15.200")],
                url="view.py?a=1",
                row={"name": "10.10.15.200", "site": "site1"},
                display_text="",
            )
        ]

        results = conductor._generate_display_texts(elements)

        assert [result.context for result in results] == [""]

    def test_unique_host_names_have_no_context(self) -> None:
        conductor = self._conductor("hosts")
        elements = [
            LivestatusResult(
                text_tokens=[("h", "myhost")],
                url="view.py?a=1",
                row={"name": "myhost", "site": "site1"},
                display_text="",
            )
        ]

        results = conductor._generate_display_texts(elements)

        assert [(result.title, result.url, result.context) for result in results] == [
            ("myhost", "view.py?a=1", "")
        ]

    def test_service_matched_by_host_address_keeps_the_service_title(self) -> None:
        conductor = self._conductor("services", {"ad": ["10.10.15.20"], "s": ["CPU"]})
        elements = [
            LivestatusResult(
                text_tokens=[("ad", "10.10.15.200"), ("s", "CPU load")],
                url="view.py?a=1",
                row={"description": "CPU load", "host_name": "myhost"},
                display_text="",
            )
        ]

        results = conductor._generate_display_texts(elements)

        assert [(result.title, result.context) for result in results] == [("CPU load", "")]

    def test_repeated_host_group_is_reported_once(self) -> None:
        conductor = self._conductor("hostgroups")
        elements = [
            LivestatusResult(
                text_tokens=[("hg", "mygroup")],
                url="view.py?a=1",
                row={"name": "mygroup", "site": "site1"},
                display_text="",
            ),
            LivestatusResult(
                text_tokens=[("hg", "mygroup")],
                url="view.py?a=2",
                row={"name": "mygroup", "site": "site2"},
                display_text="",
            ),
        ]

        results = conductor._generate_display_texts(elements)

        assert [result.title for result in results] == ["mygroup"]


class TestUrlBuilder:
    def test_the_search_parameters_are_dropped_from_the_target_url(self) -> None:
        build_url = _build_url("q=myhost&sort=alphabetic&collapse=1&provider=monitoring&po=1")

        url = build_url([("view_name", "host")])

        assert urlsplit(url).path == "view.py"
        assert _url_params(url) == {"po": "1", "view_name": "host"}


class TestGetMatchTopic:
    def test_a_single_filter_reports_its_own_topic(self) -> None:
        conductor = LivestatusQuicksearchConductor(
            {"h": ["myhost"]}, FilterBehaviour.CONTINUE, row_limit=80
        )

        assert conductor.get_match_topic() == "Host name"

    def test_combined_filters_are_reported_as_a_multi_filter(self) -> None:
        conductor = LivestatusQuicksearchConductor(
            {"h": ["myhost"], "s": ["CPU"]}, FilterBehaviour.CONTINUE, row_limit=80
        )

        assert conductor.get_match_topic() == "Multi-Filter"

    def test_an_unregistered_filter_has_no_topic(self) -> None:
        conductor = LivestatusQuicksearchConductor(
            {"nonsense": ["x"]}, FilterBehaviour.CONTINUE, row_limit=80
        )

        with pytest.raises(NotImplementedError):
            conductor.get_match_topic()


class TestLivestatusTable:
    def test_the_table_is_not_available_before_the_query_is_built(self) -> None:
        conductor = LivestatusQuicksearchConductor(
            {"h": ["myhost"]}, FilterBehaviour.CONTINUE, row_limit=80
        )

        with pytest.raises(RuntimeError):
            _ = conductor.livestatus_table

    @pytest.mark.parametrize(
        "livestatus_table, expected",
        [
            pytest.param("hosts", ["name"], id="hosts"),
            pytest.param("services", ["description", "host_name"], id="services"),
            pytest.param("hostgroups", ["name"], id="host groups"),
            pytest.param("servicegroups", ["name"], id="service groups"),
            pytest.param("", [], id="unknown table"),
        ],
    )
    def test_default_columns_depend_on_the_table(
        self, livestatus_table: str, expected: list[str]
    ) -> None:
        conductor = LivestatusQuicksearchConductor(
            {"h": ["myhost"]}, FilterBehaviour.CONTINUE, row_limit=80
        )
        conductor._livestatus_table = livestatus_table

        assert conductor._get_livestatus_default_columns() == expected


class TestGenerateLivestatusCommand:
    @staticmethod
    def _command(used_filters: UsedFilters, row_limit: int = 80) -> str:
        conductor = LivestatusQuicksearchConductor(
            used_filters, FilterBehaviour.CONTINUE, row_limit=row_limit
        )
        conductor._generate_livestatus_command()
        return conductor._livestatus_command

    @staticmethod
    def _columns(command: str) -> list[str]:
        for line in command.splitlines():
            if line.startswith("Columns: "):
                return sorted(line.removeprefix("Columns: ").split())
        raise AssertionError(f"no Columns header in {command!r}")

    def test_a_host_query_selects_the_hosts_table(self) -> None:
        command = self._command({"h": ["myhost"]})

        assert command.startswith("GET hosts\n")
        assert "Filter: name ~~ myhost" in command

    def test_the_queried_columns_are_collected_from_all_used_plugins(self) -> None:
        command = self._command({"h": ["myhost"], "s": ["CPU"]})

        assert command.startswith("GET services\n")
        assert self._columns(command) == [
            "description",
            "host_name",
            "service_description",
        ]

    def test_filters_of_different_plugins_must_all_match(self) -> None:
        command = self._command({"h": ["myhost"], "s": ["CPU"]})

        assert "Filter: host_name ~~ myhost" in command
        assert "Filter: service_description ~~ CPU" in command
        assert "And: 2" in command

    def test_one_more_row_than_the_limit_is_requested(self) -> None:
        # The extra row is what lets the conductor tell "exactly at the limit" from
        # "there is more" - see _execute_livestatus_command().
        command = self._command({"h": ["myhost"]}, row_limit=5)

        assert command.endswith("Cache: reload\nLimit: 6\nColumnHeaders: off")


class TestExecuteLivestatusCommand:
    @staticmethod
    def _conductor(row_limit: int) -> LivestatusQuicksearchConductor:
        return LivestatusQuicksearchConductor(
            {"h": ["myhost"]}, FilterBehaviour.CONTINUE, row_limit=row_limit
        )

    def test_rows_are_labelled_with_the_site_they_came_from(
        self, load_config: Config, mock_livestatus: MockLiveStatusConnection
    ) -> None:
        mock_livestatus.set_sites(["NO_SITE"])
        mock_livestatus.add_table(
            "hosts", [{"name": "myhost", "host_name": "myhost"}], site="NO_SITE"
        )
        mock_livestatus.expect_query(
            "GET hosts\nColumns: ...\nFilter: name ~~ myhost\nLimit: 81\nColumnHeaders: off",
            match_type="ellipsis",
        )
        conductor = self._conductor(row_limit=80)

        with mock_livestatus(expect_status_query=True):
            conductor.do_query()

        assert conductor.num_rows() == 1
        assert conductor._rows[0]["site"] == "NO_SITE"
        assert conductor._rows[0]["name"] == "myhost"
        assert conductor.row_limit_exceeded() is False

    def test_exceeding_the_row_limit_drops_the_probe_row(
        self, load_config: Config, mock_livestatus: MockLiveStatusConnection
    ) -> None:
        mock_livestatus.set_sites(["NO_SITE"])
        mock_livestatus.add_table(
            "hosts",
            [{"name": f"myhost{idx}", "host_name": f"myhost{idx}"} for idx in range(3)],
            site="NO_SITE",
        )
        mock_livestatus.expect_query(
            "GET hosts\nColumns: ...\nFilter: name ~~ myhost\nLimit: 3\nColumnHeaders: off",
            match_type="ellipsis",
        )
        conductor = self._conductor(row_limit=2)

        with mock_livestatus(expect_status_query=True):
            conductor.do_query()

        assert conductor.num_rows() == 2
        assert conductor.row_limit_exceeded() is True

    def test_an_empty_livestatus_response_yields_no_rows(
        self, load_config: Config, mock_livestatus: MockLiveStatusConnection
    ) -> None:
        mock_livestatus.set_sites(["NO_SITE"])
        mock_livestatus.add_table("hosts", [], site="NO_SITE")
        mock_livestatus.expect_query(
            "GET hosts\nColumns: ...\nFilter: name ~~ myhost\nLimit: 81\nColumnHeaders: off",
            match_type="ellipsis",
        )
        conductor = self._conductor(row_limit=80)

        with mock_livestatus(expect_status_query=True):
            conductor.do_query()

        assert conductor.num_rows() == 0
        assert conductor.create_results(_build_url()) == []


class TestCreateResults:
    def test_a_host_result_links_to_the_host_view_of_its_site(self) -> None:
        conductor = LivestatusQuicksearchConductor(
            {"h": ["myhost"]}, FilterBehaviour.CONTINUE, row_limit=80
        )
        conductor._livestatus_table = "hosts"
        conductor._rows = [{"site": "mysite", "name": "myhost", "host_name": "myhost"}]

        results = conductor.create_results(_build_url())

        assert [result.title for result in results] == ["myhost"]
        assert _url_params(results[0].url) == {
            "view_name": "host",
            "host": "myhost",
            "site": "mysite",
        }

    def test_a_group_result_is_not_pinned_to_a_single_site(self) -> None:
        conductor = LivestatusQuicksearchConductor(
            {"hg": ["mygroup"]}, FilterBehaviour.CONTINUE, row_limit=80
        )
        conductor._livestatus_table = "hostgroups"
        conductor._rows = [{"site": "mysite", "name": "mygroup"}]

        results = conductor.create_results(_build_url())

        assert "site" not in _url_params(results[0].url)

    def test_a_filter_that_does_not_match_the_view_is_skipped(self) -> None:
        # "hg" has no url variables for the single host view, so it must not contribute
        # anything to the result url - while "h" still does. The table is derived the
        # way production does it, so this is a combination the engine can really build.
        conductor = LivestatusQuicksearchConductor(
            {"h": ["myhost"], "hg": ["mygroup"]}, FilterBehaviour.CONTINUE, row_limit=80
        )
        conductor._determine_livestatus_table()
        conductor._rows = [
            {"site": "mysite", "name": "myhost", "host_name": "myhost", "host_groups": ["mygroup"]}
        ]

        results = conductor.create_results(_build_url())

        assert _url_params(results[0].url) == {
            "view_name": "host",
            "host": "myhost",
        }


class _FakeConductor(ABCQuicksearchConductor):
    """A conductor whose rows are handed in, so that the aggregation of the
    QuicksearchManager can be tested without talking to livestatus."""

    def __init__(
        self,
        titles: list[str],
        filter_behaviour: FilterBehaviour,
        row_limit: int,
        topic: str = "Host name",
    ) -> None:
        super().__init__({"h": ["myhost"]}, filter_behaviour, row_limit)
        self.titles = titles
        self.queried = False
        self._topic = topic

    @override
    def do_query(self) -> None:
        self.queried = True

    @override
    def num_rows(self) -> int:
        return len(self.titles)

    @override
    def remove_rows_from_end(self, num: int) -> None:
        self.titles = self.titles[:-num]

    @override
    def row_limit_exceeded(self) -> bool:
        return len(self.titles) > self._row_limit

    @override
    def get_search_url_params(self) -> HTTPVariables:
        raise NotImplementedError

    @override
    def create_results(self, build_url: UrlBuilder) -> list[SearchResult]:
        return [SearchResult(title=title, url="view.py") for title in self.titles]

    @override
    def get_match_topic(self) -> str:
        return self._topic


class TestConductSearch:
    @staticmethod
    def _manager(row_limit: int) -> QuicksearchManager:
        return QuicksearchManager(row_limit=row_limit, search_order=[], build_url=_build_url())

    def test_all_filters_are_queried_while_they_want_to_continue(self) -> None:
        first = _FakeConductor(["a"], FilterBehaviour.CONTINUE, row_limit=10)
        second = _FakeConductor(["b"], FilterBehaviour.CONTINUE, row_limit=10)

        self._manager(row_limit=10)._conduct_search([first, second])

        assert (first.queried, second.queried) == (True, True)
        assert (first.titles, second.titles) == (["a"], ["b"])

    def test_the_row_limit_is_shared_across_filters(self) -> None:
        first = _FakeConductor(["a", "b"], FilterBehaviour.CONTINUE, row_limit=3)
        second = _FakeConductor(["c", "d"], FilterBehaviour.CONTINUE, row_limit=3)

        self._manager(row_limit=3)._conduct_search([first, second])

        assert (first.titles, second.titles) == (["a", "b"], ["c"])

    def test_a_finished_filter_stops_the_remaining_ones(self) -> None:
        first = _FakeConductor(["a"], FilterBehaviour.FINISHED, row_limit=10)
        second = _FakeConductor(["b"], FilterBehaviour.CONTINUE, row_limit=10)

        self._manager(row_limit=10)._conduct_search([first, second])

        assert first.queried is True
        assert second.queried is False

    def test_an_empty_finished_filter_does_not_stop_the_remaining_ones(self) -> None:
        first = _FakeConductor([], FilterBehaviour.FINISHED, row_limit=10)
        second = _FakeConductor(["b"], FilterBehaviour.CONTINUE, row_limit=10)

        self._manager(row_limit=10)._conduct_search([first, second])

        assert second.queried is True
        assert second.titles == ["b"]

    def test_a_distinct_filter_discards_the_results_of_its_predecessors(self) -> None:
        first = _FakeConductor(["a"], FilterBehaviour.CONTINUE, row_limit=10)
        second = _FakeConductor(["b"], FilterBehaviour.FINISHED_DISTINCT, row_limit=10)
        third = _FakeConductor(["c"], FilterBehaviour.CONTINUE, row_limit=10)

        self._manager(row_limit=10)._conduct_search([first, second, third])

        assert (first.titles, second.titles) == ([], ["b"])
        assert third.queried is False


class TestEvaluateResults:
    def test_results_are_grouped_by_match_topic(self) -> None:
        manager = QuicksearchManager(row_limit=10, search_order=[], build_url=_build_url())
        conductors: list[ABCQuicksearchConductor] = [
            _FakeConductor(["myhost"], FilterBehaviour.CONTINUE, 10, topic="Host name"),
            _FakeConductor(["My alias"], FilterBehaviour.CONTINUE, 10, topic="Host alias"),
        ]

        results = list(manager._evaluate_results(conductors))

        assert [(topic, [result.title for result in items]) for topic, items in results] == [
            ("Host name", ["myhost"]),
            ("Host alias", ["My alias"]),
        ]

    def test_filters_without_results_are_left_out(self) -> None:
        manager = QuicksearchManager(row_limit=10, search_order=[], build_url=_build_url())
        conductors: list[ABCQuicksearchConductor] = [
            _FakeConductor([], FilterBehaviour.CONTINUE, 10, topic="Host name"),
        ]

        assert list(manager._evaluate_results(conductors)) == []


class TestDetermineSearchObjects:
    @staticmethod
    def _manager() -> QuicksearchManager:
        return QuicksearchManager(
            row_limit=80,
            search_order=[("h", "continue"), ("s", "finished")],
            build_url=_build_url(),
        )

    def test_an_explicit_expression_yields_a_single_aggregated_conductor(
        self, load_config: Config
    ) -> None:
        user_permissions = UserPermissions.from_config(load_config, permission_registry)

        search_objects = self._manager()._determine_search_objects(
            "h:myhost s:CPU", user_permissions
        )

        assert len(search_objects) == 1
        assert isinstance(search_objects[0], LivestatusQuicksearchConductor)
        assert search_objects[0]._used_filters == {"h": ["myhost"], "s": ["CPU"]}

    def test_a_plain_query_is_offered_to_every_configured_filter(self, load_config: Config) -> None:
        user_permissions = UserPermissions.from_config(load_config, permission_registry)

        search_objects = self._manager()._determine_search_objects("myhost", user_permissions)

        assert [
            (search_object._used_filters, search_object.filter_behaviour)
            for search_object in search_objects
        ] == [
            ({"h": ["myhost"]}, FilterBehaviour.CONTINUE),
            ({"s": ["myhost"]}, FilterBehaviour.FINISHED),
        ]

    def test_a_glob_query_is_converted_to_a_regex(self, load_config: Config) -> None:
        user_permissions = UserPermissions.from_config(load_config, permission_registry)

        search_objects = self._manager()._determine_search_objects("my*host", user_permissions)

        assert search_objects[0]._used_filters == {"h": ["my.*host"]}


class TestSearch:
    @staticmethod
    def _engine(config: Config, row_limit: int = 80) -> LivestatusSearchEngine:
        return LivestatusSearchEngine(
            config,
            Request(create_environ(query_string="q=myhost")),
            row_limit=row_limit,
            search_order=[("h", "continue")],
        )

    def test_a_host_query_is_answered_with_a_unified_result(
        self, load_config: Config, mock_livestatus: MockLiveStatusConnection
    ) -> None:
        mock_livestatus.set_sites(["NO_SITE"])
        mock_livestatus.add_table(
            "hosts", [{"name": "myhost", "host_name": "myhost"}], site="NO_SITE"
        )
        mock_livestatus.expect_query(
            "GET hosts\nColumns: ...\nFilter: name ~~ myhost\nLimit: 81\nColumnHeaders: off",
            match_type="ellipsis",
        )
        engine = self._engine(load_config)

        with mock_livestatus(expect_status_query=True):
            results = list(engine.search("myhost", provider=ProviderName.monitoring))

        assert len(results) == 1
        assert results[0].title == "myhost"
        assert results[0].topic == "Host name"
        assert results[0].provider is ProviderName.monitoring
        assert _url_params(results[0].target.url) == {
            "view_name": "host",
            "host": "myhost",
            "site": "NO_SITE",
        }

    def test_a_broken_regex_is_answered_without_querying_livestatus(
        self, load_config: Config, mock_livestatus: MockLiveStatusConnection
    ) -> None:
        mock_livestatus.set_sites(["NO_SITE"])
        engine = self._engine(load_config)

        with mock_livestatus(expect_status_query=False):
            # Consumed inside the mock, so that a lazily evaluated result would still be
            # caught trying to reach livestatus.
            results = list(engine.search("(myhost", provider=ProviderName.monitoring))

        assert results == []


class TestBasicPluginQuicksearchConductor:
    @staticmethod
    def _conductor(titles: list[str], row_limit: int) -> BasicPluginQuicksearchConductor:
        conductor = BasicPluginQuicksearchConductor(
            {"menu": ["hosts"]},
            FilterBehaviour.CONTINUE,
            UserPermissions({}, {}, {}, []),
            row_limit,
        )
        conductor._results = [SearchResult(title=title, url="index.py") for title in titles]
        return conductor

    def test_results_are_stripped_from_the_end(self) -> None:
        conductor = self._conductor(["a", "b", "c"], row_limit=10)

        conductor.remove_rows_from_end(2)

        assert conductor.num_rows() == 1

    @pytest.mark.parametrize(
        "titles, expected",
        [
            pytest.param(["a", "b"], False, id="exactly at the limit"),
            pytest.param(["a", "b", "c"], True, id="one above the limit"),
        ],
    )
    def test_the_row_limit_is_reported(self, titles: list[str], expected: bool) -> None:
        assert self._conductor(titles, row_limit=2).row_limit_exceeded() is expected

    def test_the_results_are_capped_at_the_row_limit(self) -> None:
        conductor = self._conductor(["a", "b", "c"], row_limit=2)

        assert [result.title for result in conductor.create_results(_build_url())] == ["a", "b"]

    def test_a_plugin_search_has_no_content_page_to_open(self) -> None:
        # Pressing Enter on a non-livestatus match (e.g. a monitor menu entry) has no
        # view to navigate to, so there are no search url params to build.
        with pytest.raises(NotImplementedError):
            self._conductor(["a"], row_limit=10).get_search_url_params()


class TestRemoveRowsFromEndOfLivestatusRows:
    def test_rows_are_stripped_from_the_end(self) -> None:
        conductor = LivestatusQuicksearchConductor(
            {"h": ["myhost"]}, FilterBehaviour.CONTINUE, row_limit=10
        )
        conductor._rows = [{"site": "mysite", "name": f"myhost{idx}"} for idx in range(3)]

        conductor.remove_rows_from_end(2)

        assert conductor.num_rows() == 1
