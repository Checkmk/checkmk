#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator

import pytest

from cmk.ccc.exceptions import MKGeneralException
from cmk.gui.config import active_config
from cmk.gui.search._engines._livestatus import (
    GroupMatchPlugin,
    HostLabelMatchPlugin,
    HostMatchPlugin,
    HosttagMatchPlugin,
    IncorrectLabelInputError,
    Matches,
    MonitorMenuMatchPlugin,
    ServiceLabelMatchPlugin,
    ServiceMatchPlugin,
    ServiceStateMatchPlugin,
    UsedFilters,
)
from cmk.gui.type_defs import Row
from cmk.ruleset_matcher.tags import TagConfig, TagConfigSpec, TagGroupID, TagID


class TestGroupMatchPlugin:
    @pytest.mark.parametrize(
        "group_type, expected",
        [
            pytest.param("host", "Host group", id="host groups"),
            pytest.param("service", "Service group", id="service groups"),
        ],
    )
    def test_match_topic_names_the_group_type(self, group_type: str, expected: str) -> None:
        plugin = GroupMatchPlugin(group_type=group_type, name="xg")

        assert plugin.get_match_topic() == expected

    def test_group_match_is_flagged_so_the_site_is_not_pinned(self) -> None:
        assert GroupMatchPlugin(group_type="host", name="hg").is_group_match() is True

    @pytest.mark.parametrize(
        "livestatus_table, expected",
        [
            pytest.param("hostgroups", ["name"], id="the group table carries the name itself"),
            pytest.param("hosts", ["host_groups"], id="hosts reference their groups"),
            pytest.param("services", ["host_groups"], id="services reference the host groups"),
        ],
    )
    def test_queried_columns_depend_on_the_table(
        self, livestatus_table: str, expected: list[str]
    ) -> None:
        plugin = GroupMatchPlugin(group_type="host", name="hg")

        assert plugin.get_livestatus_columns(livestatus_table) == expected

    @pytest.mark.parametrize(
        "livestatus_table, used_filters, expected",
        [
            pytest.param(
                "hostgroups",
                {"hg": ["mygroup"]},
                "Filter: name ~~ mygroup",
                id="the group table matches the name by regex",
            ),
            pytest.param(
                "hosts",
                {"hg": ["mygroup"]},
                "Filter: host_groups >= mygroup",
                id="hosts match by group membership",
            ),
            pytest.param(
                "hostgroups",
                {"hg": ["one", "two"]},
                "Filter: name ~~ one\nFilter: name ~~ two\nOr: 2",
                id="several groups are combined with Or",
            ),
            pytest.param(
                "hostgroups",
                {},
                "",
                id="no filter for this plugin yields no headers",
            ),
        ],
    )
    def test_livestatus_filters_are_built(
        self, livestatus_table: str, used_filters: UsedFilters, expected: str
    ) -> None:
        plugin = GroupMatchPlugin(group_type="host", name="hg")

        assert plugin.get_livestatus_filters(livestatus_table, used_filters) == expected

    @pytest.mark.parametrize(
        "for_view, row, expected",
        [
            pytest.param(
                "hostgroup",
                {"name": "mygroup"},
                ("mygroup", [("hostgroup", "mygroup")]),
                id="exact group view filters by the group name",
            ),
            pytest.param(
                "hostgroups",
                None,
                ("mygroup", [("hostgroup_regex", "mygroup")]),
                id="group search view filters by regex",
            ),
            pytest.param(
                "searchhost",
                None,
                ("mygroup", [("hostgroups", "mygroup")]),
                id="host search view filters by host group",
            ),
            pytest.param(
                "allservices",
                {"host_groups": ["mygroup", "other"]},
                ("mygroup|other", [("hostgroups", "mygroup|other")]),
                id="a host in several groups joins them with a pipe",
            ),
        ],
    )
    def test_matches_are_built_per_view(
        self, for_view: str, row: Row | None, expected: Matches
    ) -> None:
        plugin = GroupMatchPlugin(group_type="host", name="hg")

        assert plugin.get_matches(for_view, row, "hosts", {"hg": ["mygroup"]}, []) == expected

    def test_unsupported_view_has_no_matches(self) -> None:
        plugin = GroupMatchPlugin(group_type="host", name="hg")

        assert plugin.get_matches("host", None, "hosts", {"hg": ["mygroup"]}, []) is None


class TestServiceMatchPlugin:
    @pytest.fixture(name="plugin")
    def fixture_plugin(self) -> ServiceMatchPlugin:
        return ServiceMatchPlugin()

    def test_match_topic(self, plugin: ServiceMatchPlugin) -> None:
        assert plugin.get_match_topic() == "Service name"

    def test_the_service_description_is_queried(self, plugin: ServiceMatchPlugin) -> None:
        assert plugin.get_livestatus_columns("services") == ["service_description"]

    @pytest.mark.parametrize(
        "used_filters, expected",
        [
            pytest.param(
                {"s": ["CPU"]},
                "Filter: service_description ~~ CPU",
                id="single service pattern",
            ),
            pytest.param(
                {"s": ["CPU", "Memory"]},
                "Filter: service_description ~~ CPU\nFilter: service_description ~~ Memory\nOr: 2",
                id="several service patterns are combined with Or",
            ),
            pytest.param({}, "", id="no filter for this plugin yields no headers"),
        ],
    )
    def test_livestatus_filters_are_built(
        self, plugin: ServiceMatchPlugin, used_filters: UsedFilters, expected: str
    ) -> None:
        assert plugin.get_livestatus_filters("services", used_filters) == expected

    def test_a_matched_row_links_to_the_exact_service(self, plugin: ServiceMatchPlugin) -> None:
        matches = plugin.get_matches(
            "allservices", {"description": "CPU load"}, "services", {"s": ["CPU"]}, []
        )

        assert matches == ("CPU load", [("service", "CPU load")])

    def test_without_a_row_the_query_is_used_as_a_regex(self, plugin: ServiceMatchPlugin) -> None:
        matches = plugin.get_matches("searchsvc", None, "services", {"s": ["CPU", "Memory"]}, [])

        assert matches == ("(CPU|Memory)", [("service_regex", "(CPU|Memory)")])

    def test_unsupported_view_has_no_matches(self, plugin: ServiceMatchPlugin) -> None:
        assert plugin.get_matches("host", None, "services", {"s": ["CPU"]}, []) is None


class TestServiceStateMatchPlugin:
    @pytest.fixture(name="plugin")
    def fixture_plugin(self) -> ServiceStateMatchPlugin:
        return ServiceStateMatchPlugin()

    def test_match_topic(self, plugin: ServiceStateMatchPlugin) -> None:
        assert plugin.get_match_topic() == "Service states"

    def test_the_state_column_is_queried(self, plugin: ServiceStateMatchPlugin) -> None:
        assert plugin.get_livestatus_columns("services") == ["state"]

    @pytest.mark.parametrize(
        "used_filters, expected",
        [
            pytest.param({"st": ["ok"]}, "Filter: state = 0", id="single value"),
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
            pytest.param({"st": ["nonsense"]}, "", id="unknown state name is dropped"),
            pytest.param({}, "", id="no filter for this plugin yields no headers"),
        ],
    )
    def test_livestatus_filters_are_built(
        self, plugin: ServiceStateMatchPlugin, used_filters: UsedFilters, expected: str
    ) -> None:
        assert plugin.get_livestatus_filters("services", used_filters) == expected

    def test_each_state_becomes_a_view_checkbox(self, plugin: ServiceStateMatchPlugin) -> None:
        matches = plugin.get_matches("searchsvc", None, "services", {"st": ["warn|crit"]}, [])

        assert matches == ("", [("st1", "on"), ("st2", "on"), ("service", "")])

    def test_a_matched_row_links_to_the_exact_service(
        self, plugin: ServiceStateMatchPlugin
    ) -> None:
        matches = plugin.get_matches(
            "allservices", {"description": "CPU load"}, "services", {"st": ["crit"]}, []
        )

        assert matches == ("CPU load", [("st2", "on"), ("service", "CPU load")])

    def test_unsupported_view_has_no_matches(self, plugin: ServiceStateMatchPlugin) -> None:
        assert plugin.get_matches("host", None, "services", {"st": ["ok"]}, []) is None


class TestHostMatchPlugin:
    @pytest.mark.parametrize(
        "livestatus_field, expected",
        [
            pytest.param("name", "Host name", id="name"),
            pytest.param("address", "Hostaddress", id="address"),
            pytest.param("alias", "Host alias", id="alias"),
        ],
    )
    def test_match_topic_names_the_matched_field(
        self, livestatus_field: str, expected: str
    ) -> None:
        plugin = HostMatchPlugin(livestatus_field=livestatus_field, name="x")

        assert plugin.get_match_topic() == expected

    @pytest.mark.parametrize(
        "livestatus_table, expected",
        [
            pytest.param("hosts", ["alias", "host_name"], id="the hosts table uses bare columns"),
            pytest.param(
                "services",
                ["host_alias", "host_name"],
                id="the services table needs the host_ prefix",
            ),
        ],
    )
    def test_queried_columns_are_prefixed_outside_the_hosts_table(
        self, livestatus_table: str, expected: list[str]
    ) -> None:
        plugin = HostMatchPlugin(livestatus_field="alias", name="al")

        assert plugin.get_livestatus_columns(livestatus_table) == expected

    @pytest.mark.parametrize(
        "livestatus_table, used_filters, expected",
        [
            pytest.param(
                "hosts",
                {"h": ["myhost"]},
                "Filter: name ~~ myhost",
                id="host name in the hosts table",
            ),
            pytest.param(
                "services",
                {"h": ["myhost"]},
                "Filter: host_name ~~ myhost",
                id="host name in the services table",
            ),
            pytest.param(
                "hosts",
                {"h": ["one", "two"]},
                "Filter: name ~~ one\nFilter: name ~~ two\nOr: 2",
                id="several host patterns are combined with Or",
            ),
            pytest.param("hosts", {}, "", id="no filter for this plugin yields no headers"),
        ],
    )
    def test_livestatus_filters_are_built(
        self, livestatus_table: str, used_filters: UsedFilters, expected: str
    ) -> None:
        plugin = HostMatchPlugin(livestatus_field="name", name="h")

        assert plugin.get_livestatus_filters(livestatus_table, used_filters) == expected

    # A row is only ever handed to get_matches() together with an exact-match view
    # ("host", "allservices"): _get_target_view(exact_match=False) yields the search
    # views, and those are only reached with row=None. So the row cases below use the
    # exact views and the regex cases below use the search views.
    @pytest.mark.parametrize(
        "livestatus_field, expected_text",
        [
            pytest.param("name", "myhost", id="by name"),
            pytest.param("alias", "My alias", id="by alias"),
            pytest.param("address", "10.10.15.20", id="by address"),
        ],
    )
    def test_a_matched_row_filters_the_exact_host_view_by_its_name(
        self, livestatus_field: str, expected_text: str
    ) -> None:
        # Whichever field matched, the view is filtered by the host name - the matched
        # field only decides the text shown to the user.
        plugin = HostMatchPlugin(livestatus_field=livestatus_field, name="x")
        row = {"name": "myhost", "alias": "My alias", "address": "10.10.15.20"}

        matches = plugin.get_matches("host", row, "hosts", {"x": ["myhost"]}, [])

        assert matches == (expected_text, [("host", "myhost")])

    @pytest.mark.parametrize(
        "livestatus_field, for_view, expected",
        [
            pytest.param(
                "name",
                "searchhost",
                ("(one|two)", [("host_regex", "(one|two)")]),
                id="host search view by name",
            ),
            pytest.param(
                "alias",
                "searchhost",
                ("(one|two)", [("hostalias", "(one|two)")]),
                id="host search view by alias",
            ),
            pytest.param(
                "name",
                "searchsvc",
                ("(one|two)", [("host_regex", "(one|two)")]),
                id="service search view by name",
            ),
        ],
    )
    def test_without_a_row_the_query_is_used_as_a_regex(
        self, livestatus_field: str, for_view: str, expected: Matches
    ) -> None:
        plugin = HostMatchPlugin(livestatus_field=livestatus_field, name="x")

        assert plugin.get_matches(for_view, None, "hosts", {"x": ["one", "two"]}, []) == expected

    def test_an_address_query_is_matched_by_prefix(self) -> None:
        plugin = HostMatchPlugin(livestatus_field="address", name="ad")

        matches = plugin.get_matches("searchhost", None, "hosts", {"ad": ["10.10.15."]}, [])

        assert matches == (
            "10.10.15.",
            [("host_address", "10.10.15."), ("host_address_prefix", "yes")],
        )

    def test_a_service_row_is_filtered_by_its_host_name(self) -> None:
        plugin = HostMatchPlugin(livestatus_field="name", name="h")
        row = {"host_name": "myhost", "description": "CPU load"}

        matches = plugin.get_matches("allservices", row, "services", {"h": ["myhost"]}, [])

        assert matches == ("myhost", [("host_regex", "myhost")])

    def test_unsupported_view_has_no_matches(self) -> None:
        plugin = HostMatchPlugin(livestatus_field="name", name="h")

        assert plugin.get_matches("hostgroup", None, "hosts", {"h": ["myhost"]}, []) is None


_TAG_CONFIG: TagConfigSpec = {
    "tag_groups": [
        {
            "id": TagGroupID("os"),
            "title": "Operating system",
            "tags": [
                {"id": TagID("windows"), "title": "Windows", "aux_tags": []},
                {"id": TagID("linux"), "title": "Linux", "aux_tags": []},
            ],
        }
    ],
    "aux_tags": [{"id": TagID("snmp"), "title": "SNMP"}],
}


@pytest.fixture(name="tags")
def fixture_tags(request_context: None) -> Iterator[None]:
    original = active_config.tags
    active_config.tags = TagConfig.from_config(_TAG_CONFIG)
    try:
        yield
    finally:
        active_config.tags = original


class TestHosttagMatchPlugin:
    @pytest.fixture(name="plugin")
    def fixture_plugin(self) -> HosttagMatchPlugin:
        return HosttagMatchPlugin()

    def test_match_topic(self, plugin: HosttagMatchPlugin) -> None:
        assert plugin.get_match_topic() == "Host tag"

    def test_the_host_tags_column_is_queried(self, plugin: HosttagMatchPlugin) -> None:
        assert plugin.get_livestatus_columns("hosts") == ["host_tags"]

    @pytest.mark.parametrize(
        "used_filters, expected",
        [
            pytest.param(
                {"tg": ["os:windows"]},
                "Filter: tags = os windows",
                id="a group:tag pair filters the tag group",
            ),
            pytest.param(
                {"tg": ["windows"]},
                "Filter: host_tag_values >= windows",
                id="a bare tag value stays pre-1.6 compatible",
            ),
            pytest.param(
                {"tg": ["os:windows", "snmp:snmp"]},
                "Filter: tags = os windows\nFilter: tags = snmp snmp\nAnd: 2",
                id="several tags must all match",
            ),
            pytest.param({}, "", id="no filter for this plugin yields no headers"),
        ],
    )
    def test_livestatus_filters_are_built(
        self, plugin: HosttagMatchPlugin, used_filters: UsedFilters, expected: str
    ) -> None:
        assert plugin.get_livestatus_filters("hosts", used_filters) == expected

    def test_more_than_three_tags_are_rejected(self, plugin: HosttagMatchPlugin) -> None:
        used_filters = {"tg": ["os:windows", "os:linux", "snmp:snmp", "os:aix"]}

        with pytest.raises(MKGeneralException, match="three"):
            plugin.get_livestatus_filters("hosts", used_filters)

    @pytest.mark.usefixtures("tags")
    def test_a_matched_host_row_is_filtered_by_its_name(self, plugin: HosttagMatchPlugin) -> None:
        # A row only ever comes with an exact-match view, so "host" is the reachable
        # pairing here - the tag filters are dropped in favour of the concrete host.
        matches = plugin.get_matches(
            "host", {"name": "myhost"}, "hosts", {"tg": ["os:windows"]}, []
        )

        assert matches == ("myhost", [("host", "myhost")])

    @pytest.mark.usefixtures("tags")
    def test_a_group_tag_becomes_a_tag_filter_group(self, plugin: HosttagMatchPlugin) -> None:
        matches = plugin.get_matches("searchhost", None, "hosts", {"tg": ["os:windows"]}, [])

        assert matches == (
            "",
            [
                ("host_tag_0_grp", "os"),
                ("host_tag_0_op", "is"),
                ("host_tag_0_val", "windows"),
            ],
        )

    @pytest.mark.usefixtures("tags")
    def test_a_bare_tag_value_is_resolved_to_its_group(self, plugin: HosttagMatchPlugin) -> None:
        matches = plugin.get_matches("searchhost", None, "hosts", {"tg": ["linux"]}, [])

        assert matches == (
            "",
            [
                ("host_tag_0_grp", "os"),
                ("host_tag_0_op", "is"),
                ("host_tag_0_val", "linux"),
            ],
        )

    @pytest.mark.usefixtures("tags")
    def test_an_auxiliary_tag_becomes_an_auxtag_filter(self, plugin: HosttagMatchPlugin) -> None:
        matches = plugin.get_matches("searchhost", None, "hosts", {"tg": ["snmp"]}, [])

        assert matches == ("", [("host_auxtags_0", "snmp")])

    @pytest.mark.usefixtures("tags")
    def test_an_unknown_bare_tag_value_is_skipped(self, plugin: HosttagMatchPlugin) -> None:
        matches = plugin.get_matches("searchhost", None, "hosts", {"tg": ["nonsense"]}, [])

        assert matches == ("", [])

    @pytest.mark.usefixtures("tags")
    def test_a_service_row_still_reports_the_tag_filters(self, plugin: HosttagMatchPlugin) -> None:
        # "allservices" is a multi-filter view: the tag filters must survive even though
        # a concrete row is available, because the host name alone would widen the result.
        matches = plugin.get_matches(
            "allservices", {"host_name": "myhost"}, "services", {"tg": ["os:windows"]}, []
        )

        assert matches == (
            "",
            [
                ("host_tag_0_grp", "os"),
                ("host_tag_0_op", "is"),
                ("host_tag_0_val", "windows"),
            ],
        )

    def test_unsupported_view_has_no_matches(self, plugin: HosttagMatchPlugin) -> None:
        assert plugin.get_matches("hostgroup", None, "hosts", {"tg": ["os:windows"]}, []) is None


class TestHostLabelMatchPlugin:
    @pytest.fixture(name="plugin")
    def fixture_plugin(self) -> HostLabelMatchPlugin:
        return HostLabelMatchPlugin()

    def test_match_topic(self, plugin: HostLabelMatchPlugin) -> None:
        assert plugin.get_match_topic() == "Host labels"

    @pytest.mark.parametrize(
        "livestatus_table, expected",
        [
            pytest.param("hosts", ["labels"], id="the hosts table has its own labels"),
            pytest.param("services", ["host_labels"], id="services reference the host labels"),
        ],
    )
    def test_queried_columns_depend_on_the_table(
        self, plugin: HostLabelMatchPlugin, livestatus_table: str, expected: list[str]
    ) -> None:
        assert plugin.get_livestatus_columns(livestatus_table) == expected

    @pytest.mark.parametrize(
        "livestatus_table, expected",
        [
            pytest.param("hosts", "Filter: labels = 'os' 'linux'", id="hosts table"),
            pytest.param("services", "Filter: host_labels = 'os' 'linux'", id="services table"),
        ],
    )
    def test_livestatus_filters_are_built(
        self, plugin: HostLabelMatchPlugin, livestatus_table: str, expected: str
    ) -> None:
        filters = plugin.get_livestatus_filters(livestatus_table, {"hl": ["os:linux"]})

        assert filters == expected

    def test_several_labels_are_all_filtered(self, plugin: HostLabelMatchPlugin) -> None:
        filters = plugin.get_livestatus_filters("hosts", {"hl": ["os:linux", "site:hq"]})

        assert filters == "Filter: labels = 'os' 'linux'\nFilter: labels = 'site' 'hq'"

    def test_no_labels_yield_no_headers(self, plugin: HostLabelMatchPlugin) -> None:
        assert plugin.get_livestatus_filters("hosts", {}) == ""

    @pytest.mark.parametrize(
        "user_input",
        [
            pytest.param("oslinux", id="missing colon"),
            pytest.param("os:", id="missing value"),
            pytest.param(":linux", id="missing key"),
        ],
    )
    def test_malformed_label_input_is_rejected(
        self, plugin: HostLabelMatchPlugin, user_input: str
    ) -> None:
        with pytest.raises(IncorrectLabelInputError):
            plugin.get_livestatus_filters("hosts", {"hl": [user_input]})

    def test_the_exact_host_view_is_filtered_by_the_host_name(
        self, plugin: HostLabelMatchPlugin
    ) -> None:
        matches = plugin.get_matches("host", {"name": "myhost"}, "hosts", {"hl": ["os:linux"]}, [])

        assert matches == ("myhost", [("host", "myhost")])

    def test_search_views_are_filtered_by_the_label_group(
        self, plugin: HostLabelMatchPlugin
    ) -> None:
        matches = plugin.get_matches("searchhost", None, "hosts", {"hl": ["os:linux"]}, [])

        assert matches is not None
        text, url_vars = matches
        assert text == ""
        assert ("host_labels_1_vs_1_vs", "os:linux") in url_vars

    def test_unsupported_view_has_no_matches(self, plugin: HostLabelMatchPlugin) -> None:
        assert plugin.get_matches("hostgroup", None, "hosts", {"hl": ["os:linux"]}, []) is None


class TestServiceLabelMatchPlugin:
    @pytest.fixture(name="plugin")
    def fixture_plugin(self) -> ServiceLabelMatchPlugin:
        return ServiceLabelMatchPlugin()

    def test_match_topic(self, plugin: ServiceLabelMatchPlugin) -> None:
        assert plugin.get_match_topic() == "Service labels"

    def test_the_labels_column_is_queried(self, plugin: ServiceLabelMatchPlugin) -> None:
        assert plugin.get_livestatus_columns("services") == ["labels"]

    def test_livestatus_filters_are_built(self, plugin: ServiceLabelMatchPlugin) -> None:
        filters = plugin.get_livestatus_filters("services", {"sl": ["tier:db"]})

        assert filters == "Filter: labels = 'tier' 'db'"

    def test_a_matched_row_links_to_the_exact_service(
        self, plugin: ServiceLabelMatchPlugin
    ) -> None:
        matches = plugin.get_matches(
            "allservices", {"description": "CPU load"}, "services", {"sl": ["tier:db"]}, []
        )

        assert matches == ("", [("service", "CPU load")])

    def test_search_views_are_filtered_by_the_label_group(
        self, plugin: ServiceLabelMatchPlugin
    ) -> None:
        matches = plugin.get_matches("searchsvc", None, "services", {"sl": ["tier:db"]}, [])

        assert matches is not None
        text, url_vars = matches
        assert text == ""
        assert ("service_labels_1_vs_1_vs", "tier:db") in url_vars

    def test_unsupported_view_has_no_matches(self, plugin: ServiceLabelMatchPlugin) -> None:
        assert plugin.get_matches("searchhost", None, "services", {"sl": ["tier:db"]}, []) is None


class TestMonitorMenuMatchPlugin:
    def test_match_topic(self) -> None:
        assert MonitorMenuMatchPlugin().get_match_topic() == "Monitor"
