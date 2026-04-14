#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"

import datetime
from collections.abc import Sequence
from typing import NamedTuple
from zoneinfo import ZoneInfo

import pytest
import time_machine
from pytest_mock import MockerFixture

import cmk.utils.tags
from cmk.gui.bi import _filters as bi_filters
from cmk.gui.type_defs import Rows, VisualContext
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.visuals import _filters as filters
from cmk.gui.visuals.filter import filter_registry
from cmk.livestatus_client.testing import MockLiveStatusConnection
from tests.testlib.unit.gui.filter_table_test_helper import (
    filter_inv_table_tests,
    filter_table_tests,
    FilterTableTest,
)
from tests.testlib.unit.gui.web_test_app import SetConfig


@pytest.fixture(name="live")
def fixture_livestatus_test_config(mock_livestatus, mock_wato_folders):
    live = mock_livestatus
    live.add_table(
        "hostgroups",
        [
            {
                "name": "hg",
                "alias": "HG",
            },
            {
                "name": "hg1",
                "alias": "HG 1",
            },
        ],
    )
    live.add_table(
        "servicegroups",
        [
            {
                "name": "sg",
                "alias": "SG",
            },
            {
                "name": "sg1",
                "alias": "SG 1",
            },
        ],
    )
    live.add_table(
        "contactgroups",
        [
            {
                "name": "cg",
                "alias": "CG",
            },
            {
                "name": "cg1",
                "alias": "CG 1",
            },
        ],
    )
    live.add_table(
        "commands",
        [
            {
                "name": "cmd",
                "alias": "CMD",
            },
            {
                "name": "cmd1",
                "alias": "CMD 1",
            },
        ],
    )
    live.add_table(
        "hosts",
        [
            {
                "name": "example.com",
                "alias": "example.com alias",
                "address": "server.example.com",
                "custom_variables": {
                    "FILENAME": "/wato/hosts.mk",
                    "ADDRESS_FAMILY": "4",
                    "ADDRESS_4": "127.0.0.1",
                    "ADDRESS_6": "",
                    "TAGS": "/wato/ auto-piggyback cmk-agent ip-v4 ip-v4-only lan no-snmp prod site:heute tcp",
                },
                "contacts": [],
                "contact_groups": ["all"],
                "filename": "/wato/hosts.mk",
            }
        ],
    )
    return live


# In general filters should not affect livestatus query in case there is no variable set for them
@pytest.mark.parametrize("filter_ident", filter_registry.keys())
def test_filters_filter_with_empty_request(
    filter_ident: str, live: MockLiveStatusConnection, request_context: None
) -> None:
    if filter_ident == "hostgroupvisibility":
        expected_filter = "Filter: hostgroup_num_hosts > 0\n"
    else:
        expected_filter = ""

    with live(expect_status_query=False):
        filt = filter_registry[filter_ident]
        assert filt.filter({}) == expected_filter


class FilterTest(NamedTuple):
    ident: str
    request_vars: Sequence[tuple[str, str]]
    expected_filters: str


filter_tests = [
    FilterTest(
        ident="address_families",
        request_vars=[("address_families", "both")],
        expected_filters=("Filter: tags = ip-v4 ip-v4\nFilter: tags = ip-v6 ip-v6\nOr: 2\n"),
    ),
    FilterTest(
        ident="address_family",
        request_vars=[("address_family", "4")],
        expected_filters="Filter: tags = address_family ip-v4-only\n",
    ),
    # Testing base class FilterQueryDropdown
    FilterTest(
        ident="check_command",
        request_vars=[("check_command", "blabla")],
        expected_filters="Filter: service_check_command ~ ^blabla(!.*)?\n",
    ),
    # Testing base class FilterText
    FilterTest(
        ident="comment_author",
        request_vars=[("comment_author", "harry")],
        expected_filters="Filter: comment_author ~~ harry\n",
    ),
    FilterTest(
        ident="comment_author",
        request_vars=[("comment_author", "harry"), ("neg_comment_author", "on")],
        expected_filters="Filter: comment_author !~~ harry\n",
    ),
    # Testing base class FilterTime
    FilterTest(
        ident="comment_entry_time",
        request_vars=[
            ("comment_entry_time_from", "2001-02-03"),
            ("comment_entry_time_from_range", "abs"),
            ("comment_entry_time_until", "2002-03-04"),
            ("comment_entry_time_until_range", "abs"),
        ],
        expected_filters=(
            "Filter: comment_entry_time >= 981158400\nFilter: comment_entry_time <= 1015200000\n"
        ),
    ),
    FilterTest(
        ident="comment_entry_time",
        request_vars=[
            ("comment_entry_time_from", "2"),
            ("comment_entry_time_from_range", "3600"),
            ("comment_entry_time_until", "3"),
            ("comment_entry_time_until_range", "3600"),
        ],
        expected_filters=(
            "Filter: comment_entry_time >= 1523803800\nFilter: comment_entry_time <= 1523800200\n"
        ),
    ),
    FilterTest(
        ident="event_count",
        request_vars=[("event_count_from", "1"), ("event_count_until", "123")],
        expected_filters=("Filter: event_count >= 1\nFilter: event_count <= 123\n"),
    ),
    # Testing base class EventFilterDropdown
    FilterTest(
        ident="event_facility",
        request_vars=[("event_facility", "0")],
        expected_filters="Filter: event_facility = 0\n",
    ),
    # Testing base class FilterNagiosFlag, FilterOption
    FilterTest(
        ident="event_host_in_downtime",
        request_vars=[
            ("is_event_host_in_downtime", "0"),
        ],
        expected_filters="Filter: event_host_in_downtime = 0\n",
    ),
    FilterTest(
        ident="event_host_in_downtime",
        request_vars=[
            ("is_event_host_in_downtime", "1"),
        ],
        expected_filters="Filter: event_host_in_downtime != 0\n",
    ),
    FilterTest(
        ident="event_host_in_downtime",
        request_vars=[
            ("is_event_host_in_downtime", "-1"),
        ],
        expected_filters="",
    ),
    # Testing base class EventFilterState
    FilterTest(
        ident="event_phase",
        request_vars=[("event_phase_ack", "on"), ("event_phase_counting", "on")],
        expected_filters=("Filter: event_phase = ack\nFilter: event_phase = counting\nOr: 2\n"),
    ),
    # Testing base class FilterOption
    FilterTest(
        ident="has_performance_data",
        request_vars=[("is_has_performance_data", "0")],
        expected_filters="Filter: service_perf_data = \n",
    ),
    FilterTest(
        ident="has_performance_data",
        request_vars=[("is_has_performance_data", "1")],
        expected_filters="Filter: service_perf_data != \n",
    ),
    FilterTest(
        ident="has_performance_data",
        request_vars=[("is_has_performance_data", "-1")],
        expected_filters="",
    ),
    FilterTest(
        ident="host",
        request_vars=[("host", "blubber"), ("neg_host", "on")],
        expected_filters="Filter: host_name != blubber\n",
    ),
    # Testing base class IPAddressFilter
    FilterTest(
        ident="host_address",
        request_vars=[("host_address", "abc"), ("host_address_prefix", "yes")],
        expected_filters="Filter: host_address ~ ^abc\n",
    ),
    FilterTest(
        ident="host_address",
        request_vars=[("host_address", "abc"), ("host_address_prefix", "no")],
        expected_filters="Filter: host_address = abc\n",
    ),
    FilterTest(
        ident="host_auxtags",
        request_vars=[
            ("host_auxtags_0", "a"),
            ("host_auxtags_1", "b"),
            ("host_auxtags_2", "c"),
            ("host_auxtags_2_neg", "on"),
            ("host_auxtags_3", "d"),
        ],
        expected_filters=(
            "Filter: host_tags = 'a' 'a'\n"
            "Filter: host_tags = 'b' 'b'\n"
            "Filter: host_tags != 'c' 'c'\n"
            "Filter: host_tags = 'd' 'd'\n"
        ),
    ),
    # Testing base class ABCFilterCustomAttribute
    FilterTest(
        ident="host_custom_variable",
        request_vars=[
            ("host_custom_variable_name", "bla"),
            ("host_custom_variable_value", "blubz"),
        ],
        expected_filters="Filter: host_custom_variables ~~ BLA ^blubz\n",
    ),
    # Testing base class FilterStarred, FilterOption
    FilterTest(
        ident="host_favorites",
        request_vars=[("is_host_favorites", "0")],
        expected_filters="",
    ),
    FilterTest(
        ident="host_favorites",
        request_vars=[("is_host_favorites", "1")],
        expected_filters="Filter: host_state = -4612\n",
    ),
    FilterTest(
        ident="host_favorites",
        request_vars=[("is_host_favorites", "-1")],
        expected_filters="",
    ),
    # Testing base class LabelGroupFilter
    FilterTest(
        ident="host_labels",
        request_vars=[("host_labels_count", "0")],
        expected_filters="",
    ),
    FilterTest(
        ident="host_labels",
        request_vars=[
            ("host_labels_count", "2"),
            # Group 1
            ("host_labels_1_vs_count", "2"),
            ("host_labels_1_bool", "and"),
            ("host_labels_1_vs_1_bool", "and"),
            ("host_labels_1_vs_1_vs", "label:abc"),
            ("host_labels_1_vs_2_bool", "or"),
            ("host_labels_1_vs_2_vs", "label:xyz"),
            # Group 2
            ("host_labels_2_vs_count", "1"),
            ("host_labels_2_bool", "not"),
            ("host_labels_2_vs_1_bool", "and"),
            ("host_labels_2_vs_1_vs", "label:mno"),
        ],
        expected_filters=(
            "Filter: host_labels = 'label' 'abc'\nFilter: host_labels = 'label' 'xyz'\nOr: 2\n"
            "Filter: host_labels = 'label' 'mno'\nNegate:\nAnd: 2\n"
        ),
    ),
    # Testing base class FilterNumberRange
    FilterTest(
        ident="host_notif_number",
        request_vars=[
            ("host_notif_number_from", "10"),
            ("host_notif_number_until", "32"),
        ],
        expected_filters=(
            "Filter: current_notification_number >= 10\nFilter: current_notification_number <= 32\n"
        ),
    ),
    # Testing base class FmilterStateType, FilterTriState
    FilterTest(
        ident="host_state_type",
        request_vars=[("is_host_state_type", "0")],
        expected_filters="Filter: state_type = 0\n",
    ),
    FilterTest(
        ident="host_state_type",
        request_vars=[("is_host_state_type", "1")],
        expected_filters="Filter: state_type = 1\n",
    ),
    FilterTest(
        ident="host_state_type",
        request_vars=[("is_host_state_type", "-1")],
        expected_filters="",
    ),
    # Testing base class ABCTagFilter
    FilterTest(
        ident="host_tags",
        request_vars=[
            ("host_tag_0_grp", "address_family"),
            ("host_tag_0_op", "isnot"),
            ("host_tag_0_val", "no-ip1"),
            ("host_tag_1_grp", "address_family"),
            ("host_tag_1_op", "isnot"),
            ("host_tag_1_val", "no-ip2"),
            ("host_tag_2_grp", "address_family"),
            ("host_tag_2_op", "isnot"),
            ("host_tag_2_val", "no-ip3"),
            ("host_tag_3_grp", "address_family"),
            ("host_tag_3_op", "isnot"),
            ("host_tag_3_val", "no-ip4"),
        ],
        expected_filters=(
            "Filter: host_tags != 'address_family' 'no-ip1'\n"
            "Filter: host_tags != 'address_family' 'no-ip2'\n"
            "Filter: host_tags != 'address_family' 'no-ip3'\n"
            "Filter: host_tags != 'address_family' 'no-ip4'\n"
        ),
    ),
    # Testing base class FilterText
    FilterTest(
        ident="hostalias",
        request_vars=[("hostalias", "häääa")],
        expected_filters="Filter: host_alias ~~ häääa\n",
    ),
    FilterTest(
        ident="hostalias",
        request_vars=[("hostalias", "häääa"), ("neg_hostalias", "on")],
        expected_filters="Filter: host_alias !~~ häääa\n",
    ),
    # Testing base class FilterGroupSelection
    FilterTest(
        ident="hostgroup",
        request_vars=[("hostgroup", "grp")],
        expected_filters="Filter: hostgroup_name = grp\n",
    ),
    # Testing base class FilterMultigroup
    FilterTest(
        ident="hostgroups",
        request_vars=[
            ("hostgroups", "grp1|grp2"),
            ("neg_hostgroups", "on"),
        ],
        expected_filters=("Filter: host_groups !>= grp1\nFilter: host_groups !>= grp2\nAnd: 2\n"),
    ),
    FilterTest(
        ident="hostgroups",
        request_vars=[
            ("hostgroups", "grp1|grp2"),
        ],
        expected_filters=("Filter: host_groups >= grp1\nFilter: host_groups >= grp2\nOr: 2\n"),
    ),
    FilterTest(
        ident="hostgroupvisibility",
        request_vars=[
            ("hostgroupshowempty", "on"),
        ],
        expected_filters="",
    ),
    FilterTest(
        ident="hostgroupvisibility",
        request_vars=[],
        expected_filters="Filter: hostgroup_num_hosts > 0\n",
    ),
    FilterTest(
        ident="hostnameoralias",
        request_vars=[
            ("hostnameoralias", "abc"),
        ],
        expected_filters=("Filter: host_name ~~ abc\nFilter: host_alias ~~ abc\nOr: 2\n"),
    ),
    FilterTest(
        ident="hosts_having_service_problems",
        request_vars=[
            ("hosts_having_services_crit", "on"),
            ("hosts_having_services_pending", "on"),
        ],
        expected_filters=(
            "Filter: host_num_services_crit > 0\nFilter: host_num_services_pending > 0\nOr: 2\n"
        ),
    ),
    FilterTest(
        ident="hostsgroups_having_problems",
        request_vars=[("hostgroups_having_hosts_down", "on")],
        expected_filters=("Filter: num_hosts_down > 0\n"),
    ),
    FilterTest(
        ident="hoststate",
        request_vars=[
            ("hoststate_filled", "1"),
            ("hst0", "on"),
            ("hst1", "on"),
        ],
        expected_filters=(
            "Filter: host_state = 2\n"
            "Filter: host_has_been_checked = 1\n"
            "And: 2\n"
            "Negate:\n"
            "Filter: host_has_been_checked = 1\n"
        ),
    ),
    # Testing base class FilterECServiceLevelRange
    FilterTest(
        ident="hst_service_level",
        request_vars=[
            ("hst_service_level_lower", "10"),
            ("hst_service_level_upper", "20"),
        ],
        expected_filters=("Filter: host_custom_variable_names >= EC_SL\n"),
    ),
    FilterTest(
        ident="log_class",
        request_vars=[
            ("logclass_filled", "1"),
            ("logclass0", "on"),
            ("logclass2", "on"),
        ],
        expected_filters=("Filter: class = 0\nFilter: class = 2\nOr: 2\n"),
    ),
    FilterTest(
        ident="log_state",
        request_vars=[
            ("logst_h0", "on"),
            ("logst_h1", "on"),
            ("logst_s0", "on"),
            ("logst_s1", "on"),
        ],
        expected_filters=(
            "Filter: log_type ~ HOST .*\n"
            "Filter: log_state = 0\n"
            "And: 2\n"
            "Filter: log_type ~ HOST .*\n"
            "Filter: log_state = 1\n"
            "And: 2\n"
            "Filter: log_type ~ SERVICE .*\n"
            "Filter: log_state = 0\n"
            "And: 2\n"
            "Filter: log_type ~ SERVICE .*\n"
            "Filter: log_state = 1\n"
            "And: 2\n"
            "Or: 4\n"
        ),
    ),
    # Testing base class FilterGroupCombo
    FilterTest(
        ident="optevent_effective_contactgroup",
        request_vars=[
            ("optevent_effective_contact_group", "ding"),
        ],
        expected_filters=(
            "Filter: event_contact_groups_precedence = host\n"
            "Filter: host_contact_groups >= ding\n"
            "And: 2\n"
            "Filter: event_contact_groups_precedence = rule\n"
            "Filter: event_contact_groups >= ding\n"
            "And: 2\n"
            "Or: 2\n"
        ),
    ),
    FilterTest(
        ident="optevent_effective_contactgroup",
        request_vars=[
            ("optevent_effective_contact_group", "ding"),
            ("neg_optevent_effective_contact_group", "on"),
        ],
        expected_filters=(
            "Filter: event_contact_groups_precedence = host\n"
            "Filter: host_contact_groups !>= ding\n"
            "And: 2\n"
            "Filter: event_contact_groups_precedence = rule\n"
            "Filter: event_contact_groups !>= ding\n"
            "And: 2\n"
            "Or: 2\n"
        ),
    ),
    # Testing base class SiteFilter
    FilterTest(
        ident="site",
        request_vars=[("site", "abc")],
        expected_filters="",
    ),
    # Testing base class FilterServiceState
    FilterTest(
        ident="svchardstate",
        request_vars=[
            ("hd_filled", "1"),
            ("hdst0", "on"),
            ("hdst3", "on"),
        ],
        expected_filters=(
            "Filter: service_last_hard_state = 1\n"
            "Filter: service_has_been_checked = 1\n"
            "And: 2\n"
            "Negate:\n"
            "Filter: service_last_hard_state = 2\n"
            "Filter: service_has_been_checked = 1\n"
            "And: 2\n"
            "Negate:\n"
            "Filter: service_has_been_checked = 1\n"
        ),
    ),
    FilterTest(
        ident="wato_folder",
        request_vars=[("wato_folder", "")],
        expected_filters="",
    ),
    FilterTest(
        ident="wato_folder",
        request_vars=[("wato_folder", "x/*")],
        expected_filters="Filter: host_filename ~~ ^/wato/x/.*/\n",
    ),
    FilterTest(
        ident="wato_folder",
        request_vars=[("wato_folder", "abc/xyz")],
        expected_filters="Filter: host_filename ~ ^/wato/abc/xyz/\n",
    ),
    # Testing FilterHostnameOrAlias
    FilterTest(
        ident="hostnameoralias",
        request_vars=[("hostnameoralias", "horst")],
        expected_filters="Filter: host_name ~~ horst\nFilter: host_alias ~~ horst\nOr: 2\n",
    ),
    # Testing FilterCommaSeparatedStringList
    FilterTest(
        ident="log_contact_name",
        request_vars=[("log_contact_name", "gottlob")],
        expected_filters="Filter: log_contact_name ~ (,|^)gottlob(,|$)\n",
    ),
    FilterTest(
        ident="log_contact_name",
        request_vars=[("log_contact_name", "gott.lob"), ("neg_log_contact_name", "on")],
        expected_filters="Filter: log_contact_name ~ (,|^)gott\\.lob(,|$)\n",
    ),
]


def filter_test_id(t):
    return t.ident + ":" + ",".join(["=".join(p) for p in t.request_vars])


@pytest.mark.parametrize("test", filter_tests, ids=filter_test_id)
def test_filters_filter(test: FilterTest, set_config: SetConfig, request_context: None) -> None:
    with (
        set_config(
            wato_host_attrs=[
                {"name": "bla", "title": "Bla"}
            ],  # Needed for ABCFilterCustomAttribute
            tags=cmk.utils.tags.BuiltinTagConfig(),  # Need for ABCTagFilter
        ),
        time_machine.travel(datetime.datetime(2018, 4, 15, 16, 50, tzinfo=ZoneInfo("UTC"))),
    ):
        filt = filter_registry[test.ident]
        filter_vars = dict(filt.value())  # Default empty vars, exhaustive
        filter_vars.update(dict(test.request_vars))
        assert filt.filter(filter_vars) == test.expected_filters


@pytest.mark.parametrize("test", filter_table_tests)
def test_filters_filter_table(
    test: FilterTableTest, monkeypatch: pytest.MonkeyPatch, request_context: None
) -> None:
    # Skip deployment_has_agent in community edition - needs bakery
    if test.ident == "deployment_has_agent":
        pytest.skip("deployment_has_agent needs bakery (non-community)")

    # Needed for FilterAggrServiceUsed test
    def is_part_of_aggregation_patch(host: str, service: str) -> bool:
        return {("h", "srv1"): True}.get((host, service), False)

    monkeypatch.setattr(bi_filters, "is_part_of_aggregation", is_part_of_aggregation_patch)

    with time_machine.travel(datetime.datetime(2018, 4, 15, 16, 50, tzinfo=ZoneInfo("CET"))):
        context: VisualContext = {test.ident: dict(test.request_vars)}
        filt = filter_registry[test.ident]
        assert filt.filter_table(context, test.rows) == test.expected_rows


@pytest.mark.parametrize("test", filter_inv_table_tests)
def test_filters_filter_inv_table(test: FilterTableTest) -> None:
    pass


# Filter form is not really checked. Only checking that no exception occurs
def test_filters_display_with_empty_request(
    live: MockLiveStatusConnection, request_context: None, patch_theme: None
) -> None:
    with live:
        for filt in filter_registry.values():
            with output_funnel.plugged():
                _set_expected_queries(filt.ident, live)
                filt.display({k: "" for k in filt.htmlvars})


def _set_expected_queries(filt_ident, live):
    if filt_ident in ["hostgroups"]:
        live.expect_query("GET hostgroups\nCache: reload\nColumns: name alias\n")
        return

    if filt_ident in ["servicegroups"]:
        live.expect_query("GET servicegroups\nCache: reload\nColumns: name alias\n")
        return

    if filt_ident in [
        "contactgroups",
        "optcontactgroup",
    ]:
        live.expect_query("GET contactgroups\nCache: reload\nColumns: name alias\n")
        if filt_ident == "contactgroups":
            live.expect_query("GET contactgroups\nCache: reload\nColumns: name alias\n")
        return


class TestFilterCMKSiteStatisticsByCorePIDs:
    @pytest.fixture(name="filter_core_pid")
    def fixture_filter_core_pid(self) -> filters.FilterCMKSiteStatisticsByCorePIDs:
        assert isinstance(
            filter_core_pid := filter_registry[filters.FilterCMKSiteStatisticsByCorePIDs.ID],
            filters.FilterCMKSiteStatisticsByCorePIDs,
        )
        return filter_core_pid

    @pytest.fixture(name="patch_site_states")
    def fixture_patch_site_states(self, mocker: MockerFixture) -> None:
        mocker.patch.object(
            filters.sites,
            "states",
            return_value={
                "heute": {"core_pid": 23231, "state": "online"},
                "heute_remote_1": {"core_pid": 24610, "state": "online"},
            },
        )

    @pytest.fixture(name="livestatus_data")
    def fixture_livestatus_data(self) -> Rows:
        return [
            {
                "site": "heute",
                "service_description": "Site standalone statistics",
                "service_perf_data": "cmk_hosts_up=3;;;; cmk_hosts_down=0;;;; cmk_hosts_unreachable=0;;;; cmk_hosts_in_downtime=0;;;; cmk_services_ok=81;;;; cmk_services_in_downtime=0;;;; cmk_services_on_down_hosts=0;;;; cmk_services_warning=315;;;; cmk_services_unknown=0;;;; cmk_services_critical=408;;;;",
                "long_plugin_output": "Total hosts: 3\\nHosts in state UP: 3\\nHosts in state DOWN: 0\\nUnreachable hosts: 0\\nHosts in downtime: 0\\nTotal services: 804\\nServices in state OK: 81\\nServices in downtime: 0\\nServices of down hosts: 0\\nServices in state WARNING: 315\\nServices in state UNKNOWN: 0\\nServices in state CRITICAL: 408\\nCore PID: 28388",
                "service_metrics": [
                    "cmk_services_critical",
                    "cmk_services_unknown",
                    "cmk_services_warning",
                    "cmk_services_on_down_hosts",
                    "cmk_services_in_downtime",
                    "cmk_services_ok",
                    "cmk_hosts_in_downtime",
                    "cmk_hosts_unreachable",
                    "cmk_hosts_down",
                    "cmk_hosts_up",
                ],
                "host_name": "heute",
                "service_check_command": "check_mk-cmk_site_statistics",
            },
            {
                "site": "heute",
                "service_description": "Site heute statistics",
                "service_perf_data": "cmk_hosts_up=1;;;; cmk_hosts_down=0;;;; cmk_hosts_unreachable=0;;;; cmk_hosts_in_downtime=0;;;; cmk_services_ok=50;;;; cmk_services_in_downtime=0;;;; cmk_services_on_down_hosts=0;;;; cmk_services_warning=4;;;; cmk_services_unknown=0;;;; cmk_services_critical=4;;;;",
                "long_plugin_output": "Total hosts: 1\\nHosts in state UP: 1\\nHosts in state DOWN: 0\\nUnreachable hosts: 0\\nHosts in downtime: 0\\nTotal services: 58\\nServices in state OK: 50\\nServices in downtime: 0\\nServices of down hosts: 0\\nServices in state WARNING: 4\\nServices in state UNKNOWN: 0\\nServices in state CRITICAL: 4\\nCore PID: 23231",
                "service_metrics": [
                    "cmk_services_critical",
                    "cmk_services_unknown",
                    "cmk_services_warning",
                    "cmk_services_on_down_hosts",
                    "cmk_services_in_downtime",
                    "cmk_services_ok",
                    "cmk_hosts_in_downtime",
                    "cmk_hosts_unreachable",
                    "cmk_hosts_down",
                    "cmk_hosts_up",
                ],
                "host_name": "heute",
                "service_check_command": "check_mk-cmk_site_statistics",
            },
            {
                "site": "heute",
                "service_description": "Site heute_remote_1 statistics",
                "service_perf_data": "cmk_hosts_up=1;;;; cmk_hosts_down=0;;;; cmk_hosts_unreachable=0;;;; cmk_hosts_in_downtime=0;;;; cmk_services_ok=50;;;; cmk_services_in_downtime=0;;;; cmk_services_on_down_hosts=0;;;; cmk_services_warning=3;;;; cmk_services_unknown=0;;;; cmk_services_critical=5;;;;",
                "long_plugin_output": "Total hosts: 1\\nHosts in state UP: 1\\nHosts in state DOWN: 0\\nUnreachable hosts: 0\\nHosts in downtime: 0\\nTotal services: 58\\nServices in state OK: 50\\nServices in downtime: 0\\nServices of down hosts: 0\\nServices in state WARNING: 3\\nServices in state UNKNOWN: 0\\nServices in state CRITICAL: 5\\nCore PID: 24610",
                "service_metrics": [
                    "cmk_services_critical",
                    "cmk_services_unknown",
                    "cmk_services_warning",
                    "cmk_services_on_down_hosts",
                    "cmk_services_in_downtime",
                    "cmk_services_ok",
                    "cmk_hosts_in_downtime",
                    "cmk_hosts_unreachable",
                    "cmk_hosts_down",
                    "cmk_hosts_up",
                ],
                "host_name": "heute",
                "service_check_command": "check_mk-cmk_site_statistics",
            },
            {
                "site": "heute_remote_1",
                "service_description": "Site heute statistics",
                "service_perf_data": "cmk_hosts_up=1;;;; cmk_hosts_down=0;;;; cmk_hosts_unreachable=0;;;; cmk_hosts_in_downtime=0;;;; cmk_services_ok=50;;;; cmk_services_in_downtime=0;;;; cmk_services_on_down_hosts=0;;;; cmk_services_warning=3;;;; cmk_services_unknown=0;;;; cmk_services_critical=5;;;;",
                "long_plugin_output": "Total hosts: 1\\nHosts in state UP: 1\\nHosts in state DOWN: 0\\nUnreachable hosts: 0\\nHosts in downtime: 0\\nTotal services: 58\\nServices in state OK: 50\\nServices in downtime: 0\\nServices of down hosts: 0\\nServices in state WARNING: 3\\nServices in state UNKNOWN: 0\\nServices in state CRITICAL: 5\\nCore PID: 23231",
                "service_metrics": [
                    "cmk_services_critical",
                    "cmk_services_unknown",
                    "cmk_services_warning",
                    "cmk_services_on_down_hosts",
                    "cmk_services_in_downtime",
                    "cmk_services_ok",
                    "cmk_hosts_in_downtime",
                    "cmk_hosts_unreachable",
                    "cmk_hosts_down",
                    "cmk_hosts_up",
                ],
                "host_name": "heute_remote_1",
                "service_check_command": "check_mk-cmk_site_statistics",
            },
            {
                "site": "heute_remote_1",
                "service_description": "Site heute_remote_1 statistics",
                "service_perf_data": "cmk_hosts_up=1;;;; cmk_hosts_down=0;;;; cmk_hosts_unreachable=0;;;; cmk_hosts_in_downtime=0;;;; cmk_services_ok=50;;;; cmk_services_in_downtime=0;;;; cmk_services_on_down_hosts=0;;;; cmk_services_warning=3;;;; cmk_services_unknown=0;;;; cmk_services_critical=5;;;;",
                "long_plugin_output": "Total hosts: 1\\nHosts in state UP: 1\\nHosts in state DOWN: 0\\nUnreachable hosts: 0\\nHosts in downtime: 0\\nTotal services: 58\\nServices in state OK: 50\\nServices in downtime: 0\\nServices of down hosts: 0\\nServices in state WARNING: 3\\nServices in state UNKNOWN: 0\\nServices in state CRITICAL: 5\\nCore PID: 24610",
                "service_metrics": [
                    "cmk_services_critical",
                    "cmk_services_unknown",
                    "cmk_services_warning",
                    "cmk_services_on_down_hosts",
                    "cmk_services_in_downtime",
                    "cmk_services_ok",
                    "cmk_hosts_in_downtime",
                    "cmk_hosts_unreachable",
                    "cmk_hosts_down",
                    "cmk_hosts_up",
                ],
                "host_name": "heute_remote_1",
                "service_check_command": "check_mk-cmk_site_statistics",
            },
            {
                "site": "heute_remote_1",
                "service_description": "Site standalone statistics",
                "service_perf_data": "cmk_hosts_up=3;;;; cmk_hosts_down=0;;;; cmk_hosts_unreachable=0;;;; cmk_hosts_in_downtime=0;;;; cmk_services_ok=81;;;; cmk_services_in_downtime=0;;;; cmk_services_on_down_hosts=0;;;; cmk_services_warning=314;;;; cmk_services_unknown=0;;;; cmk_services_critical=409;;;;",
                "long_plugin_output": "Total hosts: 3\\nHosts in state UP: 3\\nHosts in state DOWN: 0\\nUnreachable hosts: 0\\nHosts in downtime: 0\\nTotal services: 804\\nServices in state OK: 81\\nServices in downtime: 0\\nServices of down hosts: 0\\nServices in state WARNING: 314\\nServices in state UNKNOWN: 0\\nServices in state CRITICAL: 409\\nCore PID: 28388",
                "service_metrics": [
                    "cmk_services_critical",
                    "cmk_services_unknown",
                    "cmk_services_warning",
                    "cmk_services_on_down_hosts",
                    "cmk_services_in_downtime",
                    "cmk_services_ok",
                    "cmk_hosts_in_downtime",
                    "cmk_hosts_unreachable",
                    "cmk_hosts_down",
                    "cmk_hosts_up",
                ],
                "host_name": "heute_remote_1",
                "service_check_command": "check_mk-cmk_site_statistics",
            },
        ]

    @pytest.fixture(name="expected_result")
    def fixture_expected_result(self) -> Rows:
        return [
            {
                "host_name": "heute",
                "long_plugin_output": "Total hosts: 1\\nHosts in state UP: 1\\nHosts in "
                "state DOWN: 0\\nUnreachable hosts: 0\\nHosts in "
                "downtime: 0\\nTotal services: 58\\nServices in state "
                "OK: 50\\nServices in downtime: 0\\nServices of down "
                "hosts: 0\\nServices in state WARNING: 4\\nServices in "
                "state UNKNOWN: 0\\nServices in state CRITICAL: "
                "4\\nCore PID: 23231",
                "service_check_command": "check_mk-cmk_site_statistics",
                "service_description": "Site heute statistics",
                "service_metrics": [
                    "cmk_services_critical",
                    "cmk_services_unknown",
                    "cmk_services_warning",
                    "cmk_services_on_down_hosts",
                    "cmk_services_in_downtime",
                    "cmk_services_ok",
                    "cmk_hosts_in_downtime",
                    "cmk_hosts_unreachable",
                    "cmk_hosts_down",
                    "cmk_hosts_up",
                ],
                "service_perf_data": "cmk_hosts_up=1;;;; cmk_hosts_down=0;;;; "
                "cmk_hosts_unreachable=0;;;; "
                "cmk_hosts_in_downtime=0;;;; cmk_services_ok=50;;;; "
                "cmk_services_in_downtime=0;;;; "
                "cmk_services_on_down_hosts=0;;;; "
                "cmk_services_warning=4;;;; cmk_services_unknown=0;;;; "
                "cmk_services_critical=4;;;;",
                "site": "heute",
            },
            {
                "host_name": "heute",
                "long_plugin_output": "Total hosts: 1\\nHosts in state UP: 1\\nHosts in "
                "state DOWN: 0\\nUnreachable hosts: 0\\nHosts in "
                "downtime: 0\\nTotal services: 58\\nServices in state "
                "OK: 50\\nServices in downtime: 0\\nServices of down "
                "hosts: 0\\nServices in state WARNING: 3\\nServices in "
                "state UNKNOWN: 0\\nServices in state CRITICAL: "
                "5\\nCore PID: 24610",
                "service_check_command": "check_mk-cmk_site_statistics",
                "service_description": "Site heute_remote_1 statistics",
                "service_metrics": [
                    "cmk_services_critical",
                    "cmk_services_unknown",
                    "cmk_services_warning",
                    "cmk_services_on_down_hosts",
                    "cmk_services_in_downtime",
                    "cmk_services_ok",
                    "cmk_hosts_in_downtime",
                    "cmk_hosts_unreachable",
                    "cmk_hosts_down",
                    "cmk_hosts_up",
                ],
                "service_perf_data": "cmk_hosts_up=1;;;; cmk_hosts_down=0;;;; "
                "cmk_hosts_unreachable=0;;;; "
                "cmk_hosts_in_downtime=0;;;; cmk_services_ok=50;;;; "
                "cmk_services_in_downtime=0;;;; "
                "cmk_services_on_down_hosts=0;;;; "
                "cmk_services_warning=3;;;; cmk_services_unknown=0;;;; "
                "cmk_services_critical=5;;;;",
                "site": "heute",
            },
        ]

    @pytest.mark.usefixtures("patch_site_states")
    def test_filter_table(
        self,
        filter_core_pid: filters.FilterCMKSiteStatisticsByCorePIDs,
        livestatus_data: Rows,
        expected_result: Rows,
    ) -> None:
        assert (
            filter_core_pid.filter_table(
                {"service_cmk_site_statistics_core_pid": {}},
                livestatus_data,
            )
            == expected_result
        )

    def test_filter_table_filter_not_active(
        self,
        filter_core_pid: filters.FilterCMKSiteStatisticsByCorePIDs,
        livestatus_data: Rows,
    ) -> None:
        assert (
            filter_core_pid.filter_table(
                {},
                livestatus_data,
            )
            == livestatus_data
        )

    @pytest.mark.usefixtures("patch_site_states")
    def test_filter_table_unsorted(
        self,
        filter_core_pid: filters.FilterCMKSiteStatisticsByCorePIDs,
        livestatus_data: Rows,
        expected_result: Rows,
    ) -> None:
        assert (
            filter_core_pid.filter_table(
                {"service_cmk_site_statistics_core_pid": {}},
                livestatus_data[::-1],
            )
            == expected_result
        )
