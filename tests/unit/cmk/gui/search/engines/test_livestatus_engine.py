#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.search._engines._livestatus import (
    FilterBehaviour,
    GroupMatchPlugin,
    HostMatchPlugin,
    LivestatusQuicksearchConductor,
    LivestatusResult,
    LivestatusSearchEngine,
    QuicksearchManager,
    ServiceStateMatchPlugin,
    UsedFilters,
)


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


class TestServiceStateMatchPlugin:
    @pytest.fixture
    def plugin(self) -> ServiceStateMatchPlugin:
        return ServiceStateMatchPlugin()

    @pytest.mark.parametrize(
        "used_filters, expected",
        [
            pytest.param(
                {"st": ["ok"]},
                "Filter: state = 0",
                id="single value",
            ),
            pytest.param(
                {"st": ["ok", "warn"]},
                "Filter: state = 0\nFilter: state = 1\nOr: 2",
                id="multiple values",
            ),
            pytest.param(
                {"st": ["ok|warn"]},
                "Filter: state = 0\nFilter: state = 1\nOr: 2",
                id="with pipe operator",
            ),
            pytest.param(
                {"st": ["ok|warn|crit"]},
                "Filter: state = 0\nFilter: state = 1\nFilter: state = 2\nOr: 3",
                id="with pipe operator multiple pipes",
            ),
            pytest.param(
                {"st": ["(ok|warn)"]},
                "Filter: state = 0\nFilter: state = 1\nOr: 2",
                id="wrapped in parentheses",
            ),
            pytest.param(
                {"st": ["ok|warn "]},
                "Filter: state = 0\nFilter: state = 1\nOr: 2",
                id="trailing right whitespace",
            ),
            pytest.param(
                {"st": [" ok|warn"]},
                "Filter: state = 0\nFilter: state = 1\nOr: 2",
                id="trailing left whitespace",
            ),
            pytest.param(
                {"st": [" ok|warn "]},
                "Filter: state = 0\nFilter: state = 1\nOr: 2",
                id="left and right whitespace",
            ),
            pytest.param(
                {"st": ["ok | warn"]},
                "Filter: state = 0\nFilter: state = 1\nOr: 2",
                id="whitespace between operator",
            ),
        ],
    )
    def test_get_livestatus_filters(
        self, plugin: ServiceStateMatchPlugin, used_filters: UsedFilters, expected: str
    ) -> None:
        livestatus_table = plugin.get_preferred_livestatus_table()
        value = plugin.get_livestatus_filters(livestatus_table, used_filters)
        assert value == expected


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
