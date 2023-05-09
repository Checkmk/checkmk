#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
from collections import namedtuple
import pytest  # type: ignore[import]

from pytest_mock import MockerFixture

import cmk.utils.version as cmk_version
import cmk.utils.tags

import cmk.gui.config
import cmk.gui.inventory
from cmk.gui.globals import html
import cmk.gui.plugins.visuals
from cmk.gui.plugins.visuals.wato import FilterWatoFolder
from cmk.gui.type_defs import VisualContext

# Triggers plugin loading
import cmk.gui.views
import cmk.gui.visuals
from cmk.gui.plugins.visuals import filters

from testlib import on_time


# mock_livestatus does not support Stats queries at the moment. We need to mock the function away
# for the "wato_folder" filter test to pass.
@pytest.fixture(name="mock_wato_folders")
def fixture_mock_wato_folders(monkeypatch):
    monkeypatch.setattr(FilterWatoFolder, "_fetch_folders", lambda s: {""})


@pytest.fixture(name="live")
def fixture_livestatus_test_config(mock_livestatus, mock_wato_folders):
    live = mock_livestatus
    live.add_table('hostgroups', [
        {"name": "hg", "alias": "HG",},
        {"name": "hg1", "alias": "HG 1",},
    ])
    live.add_table('servicegroups', [
        {"name": "sg", "alias": "SG",},
        {"name": "sg1", "alias": "SG 1",},
    ])
    live.add_table('contactgroups', [
        {"name": "cg", "alias": "CG",},
        {"name": "cg1", "alias": "CG 1",},
    ])
    live.add_table('commands', [
        {"name": "cmd", "alias": "CMD",},
        {"name": "cmd1", "alias": "CMD 1",},
    ])
    live.add_table('hosts', [{
        'name': 'example.com',
        'alias': 'example.com alias',
        'address': 'server.example.com',
        'custom_variables': {
            "FILENAME": "/wato/hosts.mk",
            "ADDRESS_FAMILY": "4",
            "ADDRESS_4": "127.0.0.1",
            "ADDRESS_6": "",
            "TAGS": "/wato/ auto-piggyback cmk-agent ip-v4 ip-v4-only lan no-snmp prod site:heute tcp",
        },
        'contacts': [],
        'contact_groups': ['all'],
        'filename': "/wato/hosts.mk",
    }])
    return live


# In general filters should not affect livestatus query in case there is no variable set for them
@pytest.mark.parametrize("filter_ident", cmk.gui.plugins.visuals.utils.filter_registry.keys())
def test_filters_filter_with_empty_request(register_builtin_html, filter_ident, live):
    if filter_ident == "hostgroupvisibility":
        expected_filter = "Filter: hostgroup_num_hosts > 0\n"
    else:
        expected_filter = ""

    with live(expect_status_query=False), html.stashed_vars():
        html.request.del_vars()

        filt = cmk.gui.plugins.visuals.utils.filter_registry[filter_ident]
        assert filt.filter(infoname="bla") == expected_filter


FilterTest = namedtuple("FilterTest", [
    "ident",
    "request_vars",
    "expected_filters",
])

filter_tests = [
    FilterTest(
        ident="address_families",
        request_vars=[('address_families', "both")],
        expected_filters=(
            "Filter: tags = ip-v4 ip-v4\n"
            "Filter: tags = ip-v6 ip-v6\n"
            "Or: 2\n"
        ),
    ),
    FilterTest(
        ident="address_family",
        request_vars=[('address_family', "4")],
        expected_filters="Filter: tags = address_family ip-v4-only\n",
    ),
    # Testing base class FilterQueryDropdown
    FilterTest(
        ident="check_command",
        request_vars=[('check_command', "blabla")],
        expected_filters="Filter: service_check_command ~ ^blabla(!.*)?$\n",
    ),
    # Testing base class FilterText
    FilterTest(
        ident="comment_author",
        request_vars=[('comment_author', "harry")],
        expected_filters="Filter: comment_author ~~ harry\n",
    ),
    FilterTest(
        ident="comment_author",
        request_vars=[('comment_author', "harry"), ('neg_comment_author', "on")],
        expected_filters="Filter: comment_author !~~ harry\n",
    ),
    # Testing base class FilterTime
    FilterTest(
        ident="comment_entry_time",
        request_vars=[
            ('comment_entry_time_from', "2001-02-03"),
            ('comment_entry_time_from_range', "abs"),
            ('comment_entry_time_until', "2002-03-04"),
            ('comment_entry_time_until_range', "abs"),
        ],
        expected_filters=(
            "Filter: comment_entry_time >= 981154800\n"
            "Filter: comment_entry_time <= 1015196400\n"
        ),
    ),
    FilterTest(
        ident="comment_entry_time",
        request_vars=[
            ('comment_entry_time_from', "2"),
            ('comment_entry_time_from_range', "3600"),
            ('comment_entry_time_until', "3"),
            ('comment_entry_time_until_range', "3600"),
        ],
        expected_filters=(
            "Filter: comment_entry_time >= 1523803800\n"
            "Filter: comment_entry_time <= 1523800200\n"
        ),
    ),
    FilterTest(
        ident="event_count",
        request_vars=[('event_count_from', "1"), ('event_count_to', "123")],
        expected_filters=(
            "Filter: event_count >= 1\n"
            "Filter: event_count <= 123\n"
        ),
    ),
    # Testing base class EventFilterDropdown
    FilterTest(
        ident="event_facility",
        request_vars=[('event_facility', "0")],
        expected_filters="Filter: event_facility = 0\n",
    ),
    # Testing base class FilterNagiosFlag, FilterTristate
    FilterTest(
        ident="event_host_in_downtime",
        request_vars=[('is_event_host_in_downtime', "0"),],
        expected_filters="Filter: event_host_in_downtime = 0\n",
    ),
    FilterTest(
        ident="event_host_in_downtime",
        request_vars=[('is_event_host_in_downtime', "1"),],
        expected_filters="Filter: event_host_in_downtime != 0\n",
    ),
    FilterTest(
        ident="event_host_in_downtime",
        request_vars=[('is_event_host_in_downtime', "-1"),],
        expected_filters="",
    ),
    # Testing base class EventFilterState
    FilterTest(
        ident="event_phase",
        request_vars=[('event_phase_ack', 'on'), ('event_phase_counting', 'on')],
        expected_filters=(
            "Filter: event_phase = ack\n"
            "Filter: event_phase = counting\n"
            "Or: 2\n"
        ),
    ),
    # Testing base class FilterNagiosExpression, FilterTristate
    FilterTest(
        ident="has_performance_data",
        request_vars=[('is_has_performance_data', "0")],
        expected_filters="Filter: service_perf_data = \n",
    ),
    FilterTest(
        ident="has_performance_data",
        request_vars=[('is_has_performance_data', "1")],
        expected_filters="Filter: service_perf_data != \n",
    ),
    FilterTest(
        ident="has_performance_data",
        request_vars=[('is_has_performance_data', "-1")],
        expected_filters="",
    ),
    FilterTest(
        ident="host",
        request_vars=[('host', "blubber"), ('neg_host', "on")],
        expected_filters="Filter: host_name != blubber\n",
    ),
    # Testing base class FilterIPAddress
    FilterTest(
        ident="host_address",
        request_vars=[('host_address', 'abc'), ('host_address_prefix', 'yes')],
        expected_filters="Filter: host_address ~ ^abc\n",
    ),
    FilterTest(
        ident="host_address",
        request_vars=[('host_address', 'abc'), ('host_address_prefix', 'no')],
        expected_filters="Filter: host_address = abc\n",
    ),
    FilterTest(
        ident="host_auxtags",
        request_vars=[
            ('host_auxtags_0', "a"),
            ('host_auxtags_1', "b"),
            ('host_auxtags_2', "c"),
            ('host_auxtags_2_neg', "on"),
            ('host_auxtags_3', "d"),
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
            ('host_custom_variable_name', "bla"),
            ('host_custom_variable_value', "blubz"),
        ],
        expected_filters="Filter: host_custom_variables ~~ BLA ^blubz\n",
    ),
    # Testing base class FilterStarred, FilterTristate
    FilterTest(
        ident="host_favorites",
        request_vars=[('is_host_favorites', '0')],
        expected_filters="",
    ),
    FilterTest(
        ident="host_favorites",
        request_vars=[('is_host_favorites', '1')],
        expected_filters="Filter: host_state = -4612\n",
    ),
    FilterTest(
        ident="host_favorites",
        request_vars=[('is_host_favorites', '-1')],
        expected_filters="",
    ),
    # Testing base class ABCLabelFilter
    FilterTest(
        ident="host_labels",
        request_vars=[('host_label', '[]')],
        expected_filters="",
    ),
    FilterTest(
        ident="host_labels",
        request_vars=[('host_label', '[{"value": "abc:axxxx"}]')],
        expected_filters="Filter: host_labels = 'abc' 'axxxx'\n",
    ),
    # Testing base class FilterNumberRange
    FilterTest(
        ident="host_notif_number",
        request_vars=[('host_notif_number_from', "10"), ('host_notif_number_until', "32"),],
        expected_filters=(
            "Filter: current_notification_number >= 10\n"
            "Filter: current_notification_number <= 32\n"
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
        request_vars=[('is_host_state_type', '-1')],
        expected_filters="",
    ),
    # Testing base class ABCTagFilter
    FilterTest(
        ident="host_tags",
        request_vars=[
            ('host_tag_0_grp', "address_family"),
            ('host_tag_0_op', "isnot"),
            ('host_tag_0_val', "no-ip1"),
            ('host_tag_1_grp', "address_family"),
            ('host_tag_1_op', "isnot"),
            ('host_tag_1_val', "no-ip2"),
            ('host_tag_2_grp', "address_family"),
            ('host_tag_2_op', "isnot"),
            ('host_tag_2_val', "no-ip3"),
            ('host_tag_3_grp', "address_family"),
            ('host_tag_3_op', "isnot"),
            ('host_tag_3_val', "no-ip4"),
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
        request_vars=[('hostalias', "häääa")],
        expected_filters=u"Filter: host_alias ~~ häääa\n",
    ),
    FilterTest(
        ident="hostalias",
        request_vars=[('hostalias', "häääa"), ('neg_hostalias', "on")],
        expected_filters=u"Filter: host_alias !~~ häääa\n",
    ),
    # Testing base class FilterGroupSelection
    FilterTest(
        ident="hostgroup",
        request_vars=[('hostgroup', "grp")],
        expected_filters="Filter: hostgroup_name = grp\n",
    ),
    # Testing base class FilterMultigroup
    FilterTest(
        ident="hostgroups",
        request_vars=[
            ('hostgroups', "grp1|grp2"),
            ('neg_hostgroups', "on"),
        ],
        expected_filters=(
            "Filter: host_groups !>= grp1\n"
            "Filter: host_groups !>= grp2\n"
            "And: 2\n"
        ),
    ),
    FilterTest(
        ident="hostgroups",
        request_vars=[
            ('hostgroups', "grp1|grp2"),
        ],
        expected_filters=(
            "Filter: host_groups >= grp1\n"
            "Filter: host_groups >= grp2\n"
            "Or: 2\n"
        ),
    ),
    FilterTest(
        ident="hostgroupvisibility",
        request_vars=[('hostgroupshowempty', "on"),],
        expected_filters="",
    ),
    FilterTest(
        ident="hostgroupvisibility",
        request_vars=[],
        expected_filters="Filter: hostgroup_num_hosts > 0\n",
    ),
    FilterTest(
        ident="hostnameoralias",
        request_vars=[('hostnameoralias', "abc"),],
        expected_filters=(
            "Filter: host_name ~~ abc\n"
            "Filter: alias ~~ abc\n"
            "Or: 2\n"
        ),
    ),
    FilterTest(
        ident="hosts_having_service_problems",
        request_vars=[
            ('hosts_having_services_crit', "on"),
            ('hosts_having_services_pending', "on"),
        ],
        expected_filters=(
            "Filter: host_num_services_crit > 0\n"
            "Filter: host_num_services_pending > 0\n"
            "Or: 2\n"
        ),
    ),
    FilterTest(
        ident="hoststate",
        request_vars=[
            ('hoststate_filled', "1"),
            ('hst0', ""),
            ('hst1', ""),
        ],
        expected_filters=(
            "Filter: host_state = 0\n"
            "Filter: host_has_been_checked = 1\n"
            "And: 2\n"
            "Negate:\n"
            "Filter: host_state = 1\n"
            "Filter: host_has_been_checked = 1\n"
            "And: 2\n"
            "Negate:\n"
            "Filter: host_state = 2\n"
            "Filter: host_has_been_checked = 1\n"
            "And: 2\n"
            "Negate:\n"
        ),
    ),
    # Testing base class FilterECServiceLevelRange
    FilterTest(
        ident="hst_service_level",
        request_vars=[
            ('hst_service_level_lower', "10"),
            ('hst_service_level_upper', "20"),
        ],
        expected_filters=(
            "Filter: host_custom_variable_names >= EC_SL\n"
        ),
    ),
    FilterTest(
        ident="log_class",
        request_vars=[
            ('logclass_filled', "1"),
            ('logclass0', "on"),
            ('logclass2', "on"),
        ],
        expected_filters=(
            'Filter: class = 0\n'
            'Filter: class = 2\n'
            'Or: 2\n'
        ),
    ),
    FilterTest(
        ident="log_state",
        request_vars=[
            ('log_state_filled', '1'),
            ('logst_h0', "on"),
            ('logst_h1', "on"),
            ('logst_s0', "on"),
            ('logst_s1', "on"),
        ],
        expected_filters=(
            'Filter: log_type ~ HOST .*\n'
            'Filter: log_state = 0\n'
            'And: 2\n'
            'Filter: log_type ~ HOST .*\n'
            'Filter: log_state = 1\n'
            'And: 2\n'
            'Filter: log_type ~ SERVICE .*\n'
            'Filter: log_state = 0\n'
            'And: 2\n'
            'Filter: log_type ~ SERVICE .*\n'
            'Filter: log_state = 1\n'
            'And: 2\n'
            'Or: 4\n'
        ),
    ),
    # Testing base class FilterGroupCombo
    FilterTest(
        ident="optevent_effective_contactgroup",
        request_vars=[
            ('optevent_effective_contact_group', "ding"),
        ],
        expected_filters=(
            'Filter: event_contact_groups_precedence = host\n'
            'Filter: host_contact_groups >= ding\n'
            'And: 2\n'
            'Filter: event_contact_groups_precedence = rule\n'
            'Filter: event_contact_groups >= ding\n'
            'And: 2\n'
            'Or: 2\n'
        ),
    ),
    FilterTest(
        ident="optevent_effective_contactgroup",
        request_vars=[
            ('optevent_effective_contact_group', "ding"),
            ('neg_optevent_effective_contact_group', "on"),
        ],
        expected_filters=(
            'Filter: event_contact_groups_precedence = host\n'
            'Filter: host_contact_groups !>= ding\n'
            'And: 2\n'
            'Filter: event_contact_groups_precedence = rule\n'
            'Filter: event_contact_groups !>= ding\n'
            'And: 2\n'
            'Or: 2\n'
        ),
    ),
    # Testing base class SiteFilter
    FilterTest(
        ident="site",
        request_vars=[('site', "abc")],
        expected_filters="",
    ),
    # Testing base class FilterServiceState
    FilterTest(
        ident="svchardstate",
        request_vars=[
            ('hd_filled', '1'),
            ('hdst0', 'on'),
            ('hdst3', 'on'),
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
        ),
    ),
    FilterTest(
        ident="wato_folder",
        request_vars=[('wato_folder', "")],
        expected_filters="",
    ),
    FilterTest(
        ident="wato_folder",
        request_vars=[('wato_folder', "x/*")],
        expected_filters="Filter: host_filename ~~ ^/wato/x/.*/\n",
    ),
    FilterTest(
        ident="wato_folder",
        request_vars=[('wato_folder', "abc/xyz")],
        expected_filters="Filter: host_filename ~ ^/wato/abc/xyz/\n",
    ),
    # Testing FilterHostnameOrAlias
    FilterTest(
        ident="hostnameoralias",
        request_vars=[('hostnameoralias', "horst")],
        expected_filters="Filter: host_name ~~ horst\nFilter: alias ~~ horst\nOr: 2\n",
    ),
    # Testing FilterCommaSeparatedStringList
    FilterTest(
        ident="log_contact_name",
        request_vars=[('log_contact_name', "gottlob")],
        expected_filters="Filter: log_contact_name ~ (,|^)gottlob(,|$)\n",
    ),
    FilterTest(
        ident="log_contact_name",
        request_vars=[('log_contact_name', "gott.lob"),('neg_log_contact_name', "on")],
        expected_filters="Filter: log_contact_name ~ (,|^)gott\\.lob(,|$)\n",
    ),
]


def filter_test_id(t):
    return t.ident + ":" + ",".join(["=".join(p) for p in t.request_vars])


@pytest.mark.parametrize("test", filter_tests, ids=filter_test_id)
def test_filters_filter(register_builtin_html, test, monkeypatch):
    # Needed for ABCFilterCustomAttribute
    monkeypatch.setattr(cmk.gui.config, "wato_host_attrs", [{"name": "bla", "title": "Bla"}])

    # Need for ABCTagFilter
    monkeypatch.setattr(cmk.gui.config, "tags", cmk.utils.tags.BuiltinTagConfig())

    with html.stashed_vars(), on_time('2018-04-15 16:50', 'CET'):
        html.request.del_vars()
        for key, val in test.request_vars:
            html.request.set_var(key, val)

        filt = cmk.gui.plugins.visuals.utils.filter_registry[test.ident]
        assert filt.filter(infoname="bla") == test.expected_filters

FilterTableTest = namedtuple("FilterTableTest", [
    "ident",
    "request_vars",
    "rows",
    "expected_rows",
])


def get_inventory_data_patch(inventory, path):
    return inventory[path]


filter_table_tests = [
    # Testing base class BIStatusFilter
    FilterTableTest(
        ident="aggr_assumed_state",
        request_vars=[('bias0', "on"), ('bias1', "on"), ('bias_filled', '1')],
        rows=[
            {"aggr_assumed_state": {"state": 0}},
            {"aggr_assumed_state": {"state": 1}},
            {"aggr_assumed_state": {"state": 2}},
        ],
        expected_rows=[
            {"aggr_assumed_state": {"state": 0}},
            {"aggr_assumed_state": {"state": 1}},
        ],
    ),
    # Testing base class Filter
    FilterTableTest(
        ident="aggr_group",
        request_vars=[('aggr_group', 'blä')],
        rows=[
            {"aggr_group": "blub"},
            {"aggr_group": u"blä"},
        ],
        expected_rows=[
            {"aggr_group": u"blä"},
        ],
    ),
    FilterTableTest(
        ident="aggr_hosts",
        request_vars=[
            ('aggr_host_host', "z"),
        ],
        rows=[
            {"aggr_hosts": [("s", "a"), ("s", "z")]},
            {"aggr_hosts": [("s", "a"), ("s", "c")]},
            {"aggr_hosts": [("s", "a"), ("s", "g")]},
            {"aggr_hosts": [("s", "b"), ("s", "z")]},
        ],
        expected_rows=[
            {"aggr_hosts": [("s", "a"), ("s", "z")]},
            {"aggr_hosts": [("s", "b"), ("s", "z")]},
        ],
    ),
    FilterTableTest(
        ident="aggr_hosts",
        request_vars=[
            ('aggr_host_site', ""),
            ('aggr_host_host', "z"),
        ],
        rows=[
            {"aggr_hosts": [("s", "a"), ("s", "z")]},
            {"aggr_hosts": [("s", "a"), ("s", "c")]},
            {"aggr_hosts": [("s", "a"), ("s", "g")]},
            {"aggr_hosts": [("s", "b"), ("s", "z")]},
        ],
        expected_rows=[
            {"aggr_hosts": [("s", "a"), ("s", "z")]},
            {"aggr_hosts": [("s", "b"), ("s", "z")]},
        ],
    ),
    FilterTableTest(
        ident="aggr_hosts",
        request_vars=[
            ('aggr_host_site', "d"),
            ('aggr_host_host', "z"),
        ],
        rows=[
            {"aggr_hosts": [("s", "a"), ("s", "z")]},
            {"aggr_hosts": [("s", "a"), ("s", "c")]},
            {"aggr_hosts": [("s", "a"), ("s", "g")]},
            {"aggr_hosts": [("s", "b"), ("s", "z")]},
        ],
        expected_rows=[
            {"aggr_hosts": [("s", "a"), ("s", "z")]},
            {"aggr_hosts": [("s", "b"), ("s", "z")]},
        ],
    ),
    # Testing base class BITextFilter
    FilterTableTest(
        ident="aggr_name",
        request_vars=[('aggr_name', "a")],
        rows=[
            {"aggr_name": "a"},
            {"aggr_name": "aaa"},
            {"aggr_name": "b"},
            {"aggr_name": "c"},
        ],
        expected_rows=[
            {"aggr_name": "a"},
        ],
    ),
    # Testing base class FilterTriState
    FilterTableTest(
        ident="aggr_service_used",
        request_vars=[('is_aggr_service_used', "0")],
        rows=[
            {"site": "s", "host_name": "h", "service_description": "srv1"},
            {"site": "s", "host_name": "h", "service_description": "srv2"},
            {"site": "s", "host_name": "h2", "service_description": "srv2"},
        ],
        expected_rows=[
            {'host_name': 'h', 'service_description': 'srv2', 'site': 's'},
            {'host_name': 'h2', 'service_description': 'srv2', 'site': 's'},
        ],
    ),
    FilterTableTest(
        ident="aggr_service_used",
        request_vars=[('is_aggr_service_used', "1")],
        rows=[
            {"site": "s", "host_name": "h", "service_description": "srv1"},
            {"site": "s", "host_name": "h", "service_description": "srv2"},
            {"site": "s", "host_name": "h2", "service_description": "srv2"},
        ],
        expected_rows=[
            {"site": "s", "host_name": "h", "service_description": "srv1"},
        ],
    ),
    FilterTableTest(
        ident="aggr_service_used",
        request_vars=[('is_aggr_service_used', "-1")],
        rows=[
            {"site": "s", "host_name": "h", "service_description": "srv1"},
            {"site": "s", "host_name": "h", "service_description": "srv2"},
            {"site": "s", "host_name": "h2", "service_description": "srv2"},
            {"site": "b", "host_name": "h", "service_description": "srv1"},
        ],
        expected_rows=[
            {"site": "s", "host_name": "h", "service_description": "srv1"},
            {"site": "s", "host_name": "h", "service_description": "srv2"},
            {"site": "s", "host_name": "h2", "service_description": "srv2"},
            {"site": "b", "host_name": "h", "service_description": "srv1"},
        ],
    ),
    # Testing base class DeploymentTristateFilter
    FilterTableTest(
        ident="deployment_has_agent",
        request_vars=[('is_deployment_has_agent', "0")],
        rows=[
            {"host_name": "abc"},
            {"host_name": "zzz"},
        ],
        expected_rows=[
            {"host_name": "zzz"},
        ],
    ),
    FilterTableTest(
        ident="deployment_has_agent",
        request_vars=[('is_deployment_has_agent', "1")],
        rows=[
        ],
        expected_rows=[
        ],
    ),
    FilterTableTest(
        ident="deployment_has_agent",
        request_vars=[('is_deployment_has_agent', "-1")],
        rows=[
            {"host_name": "abc"},
            {"host_name": "zzz"},
        ],
        expected_rows=[
            {"host_name": "abc"},
            {"host_name": "zzz"},
        ],
    ),
    FilterTableTest(
        ident="discovery_state",
        request_vars=[
            ('discovery_state_ignored', "on"),
            ('discovery_state_vanished', "on"),
            ("discovery_state_unmonitored", ""),
        ],
        rows=[
            {"discovery_state": "ignored"},
            {"discovery_state": "vanished"},
            {"discovery_state": "unmonitored"},
        ],
        expected_rows=[
            {"discovery_state": "ignored"},
            {"discovery_state": "vanished"},
        ],
    ),
    FilterTableTest(
        ident="has_inv",
        request_vars=[
            ('is_has_inv', '0'),
        ],
        rows=[
            {"host_inventory": {}},
            {"host_inventory": {"a": "b"}},
        ],
        expected_rows=[
            {"host_inventory": {}},
        ]
    ),
    FilterTableTest(
        ident="has_inv",
        request_vars=[
            ('is_has_inv', '1'),
        ],
        rows=[
            {"host_inventory": {}},
            {"host_inventory": {"a": "b"}},
        ],
        expected_rows=[
            {"host_inventory": {"a": "b"}},
        ]
    ),
    FilterTableTest(
        ident="has_inv",
        request_vars=[
            ('is_has_inv', '-1'),
        ],
        rows=[
            {"host_inventory": {}},
            {"host_inventory": {"a": "b"}},
        ],
        expected_rows=[
            {"host_inventory": {}},
            {"host_inventory": {"a": "b"}},
        ]
    ),
    # Testing base class FilterInvText
    FilterTableTest(
        ident="inv_software_os_vendor",
        request_vars=[
            ('inv_software_os_vendor', "bla"),
        ],
        rows=[
            # Not real inventory structures, just input for our monkeypatched function
            {"host_inventory": {".software.os.vendor": "bla"}},
            {"host_inventory": {".software.os.vendor": "blabla"}},
            {"host_inventory": {".software.os.vendor": "ag blabla"}},
            {"host_inventory": {".software.os.vendor": "blu"}},
        ],
        expected_rows=[
            {"host_inventory": {".software.os.vendor": "bla"}},
            {"host_inventory": {".software.os.vendor": "blabla"}},
            {"host_inventory": {".software.os.vendor": "ag blabla"}},
        ],
    ),
    # Testing base class FilterInvFloat
    FilterTableTest(
        ident="inv_hardware_cpu_bus_speed",
        request_vars=[
            ('inv_hardware_cpu_bus_speed_from', "10"),
            ('inv_hardware_cpu_bus_speed_to', "20"),
        ],
        rows=[
            # Not real inventory structures, just input for our monkeypatched function
            {"host_inventory": {".hardware.cpu.bus_speed": 1000000}},
            {"host_inventory": {".hardware.cpu.bus_speed": 15000000}},
            {"host_inventory": {".hardware.cpu.bus_speed": 21000000}},
        ],
        expected_rows=[
            {"host_inventory": {".hardware.cpu.bus_speed": 15000000}},
        ],
    ),
    # Testing base class FilterInvtableText
    FilterTableTest(
        ident="invbackplane_description",
        request_vars=[
            ('invbackplane_description', "lulu"),
        ],
        rows=[
            {"invbackplane_description": "lulu"},
            {"invbackplane_description": "lele"},
        ],
        expected_rows=[
            {"invbackplane_description": "lulu"},
        ],
    ),
    # Testing base class FilterInvtableVersion
    FilterTableTest(
        ident="invswpac_package_version",
        request_vars=[
            ('invswpac_package_version_from', "1.0"),
            ('invswpac_package_version_to', "3.0"),
        ],
        rows=[
            {"invswpac_package_version": "0.5"},
            {"invswpac_package_version": "0.5.1"},
            {"invswpac_package_version": "1.5.1"},
            {"invswpac_package_version": "2.0.0"},
            {"invswpac_package_version": "4.5.1"},
        ],
        expected_rows=[
            {"invswpac_package_version": "1.5.1"},
            {"invswpac_package_version": "2.0.0"},
        ],
    ),
    # Testing base class FilterInvtableIDRange
    FilterTableTest(
        ident="invinterface_index",
        request_vars=[
            ('invinterface_index_from', "3"),
            ('invinterface_index_to', "10"),
        ],
        rows=[
            {"invinterface_index": 1},
            {"invinterface_index": 3},
            {"invinterface_index": 5},
            {"invinterface_index": 11},
        ],
        expected_rows=[
            {"invinterface_index": 3},
            {"invinterface_index": 5},
        ]
    ),
    # Testing base class FilterInvtableOperStatus
    FilterTableTest(
        ident="invinterface_oper_status",
        request_vars=[
            ('invinterface_oper_status_3', 'on'),
        ],
        rows=[
            {"invinterface_oper_status": 1},
            {"invinterface_oper_status": 3},
            {"invinterface_oper_status": 5},
        ],
        expected_rows=[
            {"invinterface_oper_status": 3},
        ],
    ),
    # Testing base class FilterInvtableAdminStatus
    FilterTableTest(
        ident="invinterface_admin_status",
        request_vars=[('invinterface_admin_status', "1")],
        rows=[
            {"invinterface_admin_status": "1"},
            {"invinterface_admin_status": "2"},
        ],
        expected_rows=[
            {"invinterface_admin_status": "1"},
        ],
    ),
    FilterTableTest(
        ident="invinterface_admin_status",
        request_vars=[('invinterface_admin_status', "2")],
        rows=[
            {"invinterface_admin_status": "1"},
            {"invinterface_admin_status": "2"},
        ],
        expected_rows=[
            {"invinterface_admin_status": "2"},
        ],
    ),
    FilterTableTest(
        ident="invinterface_admin_status",
        request_vars=[('invinterface_admin_status', "-1")],
        rows=[
            {"invinterface_admin_status": "1"},
            {"invinterface_admin_status": "2"},
        ],
        expected_rows=[
            {"invinterface_admin_status": "1"},
            {"invinterface_admin_status": "2"},
        ],
    ),
    # Testing base class FilterInvtableAvailable
    FilterTableTest(
        ident="invinterface_available",
        request_vars=[
            ('invinterface_available', "no"),
        ],
        rows=[
            {"invinterface_available": False},
            {"invinterface_available": True},
        ],
        expected_rows=[
            {"invinterface_available": False},
        ],
    ),
    FilterTableTest(
        ident="invinterface_available",
        request_vars=[
            ('invinterface_available', "yes"),
        ],
        rows=[
            {"invinterface_available": False},
            {"invinterface_available": True},
        ],
        expected_rows=[
            {"invinterface_available": True},
        ],
    ),
    FilterTableTest(
        ident="invinterface_available",
        request_vars=[
            ('invinterface_available', ""),
        ],
        rows=[
            {"invinterface_available": False},
            {"invinterface_available": True},
        ],
        expected_rows=[
            {"invinterface_available": False},
            {"invinterface_available": True},
        ],
    ),
    # Testing base class FilterInvtableInterfaceType
    FilterTableTest(
        ident="invinterface_port_type",
        request_vars=[
            ('invinterface_port_type', "2|3|10"),
        ],
        rows=[
            {"invinterface_port_type": "1"},
            {"invinterface_port_type": "2"},
            {"invinterface_port_type": "10"},
        ],
        expected_rows=[
            {"invinterface_port_type": "2"},
            {"invinterface_port_type": "10"},
        ],
    ),
    # Testing base class FilterInvtableTimestampAsAge
    FilterTableTest(
        ident="invinterface_last_change",
        request_vars=[
            ('invinterface_last_change_from_days', "1"),
            ('invinterface_last_change_to_days', "5"),
        ],
        rows=[
            {"invinterface_last_change": 1523811000},
            {"invinterface_last_change": 1523811000-(60*60*24*10)},
            {"invinterface_last_change": 1523811000-(60*60*24*4)},
        ],
        expected_rows=[
            {"invinterface_last_change": 1523811000-(60*60*24*4)},
        ],
    ),
    # FilterECServiceLevelRange
    FilterTableTest(
        ident="svc_service_level",
        request_vars=[('svc_service_level_lower', "1"), ('svc_service_level_upper', "3")],
        rows=[
            {"service_custom_variable_values": ["0","custom_1","custom_2"]},
            {"service_custom_variable_values": ["1","custom_1","custom_2"]},
            {"service_custom_variable_values": ["2","custom_1","custom_2"]},
            {"service_custom_variable_values": ["3","custom_1","custom_2"]},
            {"service_custom_variable_values": ["4","custom_1","custom_2"]},
        ],
        expected_rows=[
            {"service_custom_variable_values": ["1","custom_1","custom_2"]},
            {"service_custom_variable_values": ["2","custom_1","custom_2"]},
            {"service_custom_variable_values": ["3","custom_1","custom_2"]},
        ],
    ),
    FilterTableTest(
        ident="hst_service_level",
        request_vars=[('hst_service_level_lower', "1")],
        rows=[
            {"host_custom_variable_values": ["","","127.0.0.1","/wato/ auto-piggyback cmk-agent","/wato/hosts.mk","0"]},
            {"host_custom_variable_values": ["","","127.0.0.1","/wato/ auto-piggyback cmk-agent","/wato/hosts.mk","1"]},
            {"host_custom_variable_values": ["","","127.0.0.1","/wato/ auto-piggyback cmk-agent","/wato/hosts.mk","2"]},
        ],
        expected_rows=[
            {"host_custom_variable_values": ["","","127.0.0.1","/wato/ auto-piggyback cmk-agent","/wato/hosts.mk","1"]},
        ],
    ),
    FilterTableTest(
        ident="hst_service_level",
        request_vars=[('hst_service_level_upper', "2")],
        rows=[
            {"host_custom_variable_values": ["","","127.0.0.1","/wato/ auto-piggyback cmk-agent","/wato/hosts.mk","0"]},
            {"host_custom_variable_values": ["","","127.0.0.1","/wato/ auto-piggyback cmk-agent","/wato/hosts.mk","1"]},
            {"host_custom_variable_values": ["","","127.0.0.1","/wato/ auto-piggyback cmk-agent","/wato/hosts.mk","2"]},
        ],
        expected_rows=[
            {"host_custom_variable_values": ["","","127.0.0.1","/wato/ auto-piggyback cmk-agent","/wato/hosts.mk","2"]},
        ],
    ),
    # TODO: Testing base class FilterHistoric
    #FilterTableTest(
    #    ident="host_metrics_hist",
    #    request_vars=[
    #        ('cutoff', "10"),
    #    ],
    #    rows=[

    #    ],
    #    expected_rows=[

    #    ],
    #),
]


@pytest.mark.parametrize("test", filter_table_tests)
@pytest.mark.usefixtures("load_plugins")
def test_filters_filter_table(register_builtin_html, test, monkeypatch):
    # Needed for DeploymentTristateFilter test
    def deployment_states(host_name):
        return {
            "abc": {
                "target_aghash": "abc",
            },
            "zzz": {},
        }[host_name]

    if not cmk_version.is_raw_edition():
        import cmk.gui.cee.agent_bakery as agent_bakery  # pylint: disable=redefined-outer-name,import-outside-toplevel,no-name-in-module
        monkeypatch.setattr(agent_bakery, "get_cached_deployment_status", deployment_states)

    # Needed for FilterInvFloat test
    monkeypatch.setattr(cmk.gui.inventory, "get_inventory_data", get_inventory_data_patch)

    # Needed for FilterAggrServiceUsed test
    def is_part_of_aggregation_patch(host, service):
        return {
            ("h", "srv1"): True
        }.get((host, service), False)

    monkeypatch.setattr(cmk.gui.bi, "is_part_of_aggregation", is_part_of_aggregation_patch)

    with html.stashed_vars(), on_time('2018-04-15 16:50', 'CET'):
        if test.ident in ["aggr_name", "aggr_group"]:
            context: VisualContext = {test.ident: dict(test.request_vars)}
        else:
            context = {}
            html.request.del_vars()
            for key, val in test.request_vars:
                html.request.set_var(key, val)

        # TODO: Fix this for real...
        if not cmk_version.is_raw_edition or test.ident != "deployment_has_agent":
            filt = cmk.gui.plugins.visuals.utils.filter_registry[test.ident]
            assert filt.filter_table(context, test.rows) == test.expected_rows


# Filter form is not really checked. Only checking that no exception occurs
def test_filters_display_with_empty_request(register_builtin_html, live):
    with live, html.stashed_vars():
        html.request.del_vars()

        for filt in cmk.gui.plugins.visuals.utils.filter_registry.values():
            with html.plugged():
                _set_expected_queries(filt.ident, live)
                filt.display()


def _set_expected_queries(filt_ident, live):
    if filt_ident in ["hostgroups", "opthostgroup", "hostgroup"]:
        live.expect_query(
            'GET hostgroups\nCache: reload\nColumns: name alias\n'
        )
        if filt_ident == "hostgroups":
            live.expect_query(
                'GET hostgroups\nCache: reload\nColumns: name alias\n'
            )
        return

    if filt_ident in [ "servicegroups", "optservicegroup", "servicegroup" ]:
        live.expect_query(
            'GET servicegroups\nCache: reload\nColumns: name alias\n'
        )
        if filt_ident == "servicegroups":
            live.expect_query(
                'GET servicegroups\nCache: reload\nColumns: name alias\n'
            )
        return

    if filt_ident in ["contactgroups", "optcontactgroup", "opthost_contactgroup",
            "optservice_contactgroup", "optevent_effective_contactgroup"]:
        live.expect_query(
            'GET contactgroups\nCache: reload\nColumns: name alias\n'
        )
        if filt_ident == "contactgroups":
            live.expect_query(
                'GET contactgroups\nCache: reload\nColumns: name alias\n'
            )
        return

    if filt_ident in ["host_check_command", "check_command"]:
        live.expect_query(
            'GET commands\nCache: reload\nColumns: name\nColumnHeaders: off'
        )

class TestFilterCMKSiteStatisticsByCorePIDs:
    @pytest.fixture(name="filter_core_pid")
    def fixture_filter_core_pid(self) -> filters.FilterCMKSiteStatisticsByCorePIDs:
        assert isinstance(
            filter_core_pid := filters.filter_registry[
                filters.FilterCMKSiteStatisticsByCorePIDs.ID
            ],
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
    def fixture_livestatus_data(self) -> filters.Rows:
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
    def fixture_expected_result(self) -> filters.Rows:
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
        livestatus_data: filters.Rows,
        expected_result: filters.Rows,
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
        livestatus_data: filters.Rows,
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
        livestatus_data: filters.Rows,
        expected_result: filters.Rows,
    ) -> None:
        assert (
            filter_core_pid.filter_table(
                {"service_cmk_site_statistics_core_pid": {}},
                livestatus_data[::-1],
            )
            == expected_result
        )
