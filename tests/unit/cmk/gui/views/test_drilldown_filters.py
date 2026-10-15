#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.gui.data_source import data_source_registry
from cmk.gui.type_defs import FilterHTTPVariables, FilterName
from cmk.gui.views.drilldown_filters import drilldown_filters, ROW_FILTERS, RowValues
from cmk.gui.visuals.filter import filter_registry
from tests.testlib.unit.gui.web_test_app import SetConfig

_HOST_ROW: RowValues = {
    "site": "heute",
    "host_name": "web01",
    "host_state": 1,
    "host_has_been_checked": 1,
    "host_filename": "/wato/servers/linux/hosts.mk",
    "host_groups": ["linux"],
    "host_labels": {"cmk/os_family": "linux", "env": "prod"},
    "host_tags": {"criticality": "prod", "snmp_ds": "no-snmp", "tcp": "tcp"},
}


_REGISTERING_ONLY_THE_COUNT = {"host_labels", "service_labels"}

_VALUED_CASES = [
    pytest.param("siteopt", _HOST_ROW, [], {"site": "heute"}, id="site"),
    pytest.param("host", _HOST_ROW, [], {"host": "web01"}, id="host"),
    pytest.param("hoststate", _HOST_ROW, [], {"hst1": "on"}, id="host state"),
    pytest.param(
        "hoststate",
        {"host_name": "web01", "host_state": 0, "host_has_been_checked": 0},
        [],
        {"hstp": "on"},
        id="pending host",
    ),
    pytest.param("wato_folder", _HOST_ROW, [], {"wato_folder": "servers/linux"}, id="folder"),
    pytest.param(
        "wato_folder",
        {"host_filename": "/wato/hosts.mk"},
        [],
        {"wato_folder": ""},
        id="root folder",
    ),
    pytest.param("opthostgroup", _HOST_ROW, [], {"opthost_group": "linux"}, id="host group"),
    pytest.param(
        "host_tags",
        _HOST_ROW,
        ["criticality", "snmp_ds"],
        {
            "host_tag_0_grp": "criticality",
            "host_tag_0_op": "is",
            "host_tag_0_val": "prod",
            "host_tag_1_grp": "snmp_ds",
            "host_tag_1_op": "is",
            "host_tag_1_val": "no-snmp",
        },
        id="host tags",
    ),
    pytest.param("host_auxtags", _HOST_ROW, ["tcp"], {"host_auxtags_0": "tcp"}, id="aux tag"),
    pytest.param(
        "log_state",
        {"log_type": "SERVICE ALERT", "log_state": 2},
        [],
        {"logst_s2": "on"},
        id="service alert",
    ),
    pytest.param(
        "log_state",
        {"log_type": "INITIAL HOST STATE", "log_state": 1},
        [],
        {"logst_h1": "on"},
        id="initial host state",
    ),
    pytest.param(
        "aggr_state",
        {"aggr_state": {"state": 2, "output": ""}},
        [],
        {"birs_filled": "1", "birs2": "on"},
        id="aggregation state",
    ),
    pytest.param(
        "aggr_assumed_state",
        {"aggr_assumed_state": None},
        [],
        {"bias_filled": "1", "biasn": "on"},
        id="no assumed state",
    ),
    pytest.param(
        "event_facility", {"event_facility": 0}, [], {"event_facility": "0"}, id="facility"
    ),
    pytest.param(
        "event_host_in_downtime",
        {"event_host_in_downtime": 0},
        [],
        {"is_event_host_in_downtime": "0"},
        id="event host not in downtime",
    ),
    pytest.param(
        "optevent_effective_contactgroup",
        {
            "event_contact_groups_precedence": "rule",
            "event_contact_groups": ["ops"],
            "host_contact_groups": ["all", "linux"],
        },
        [],
        {"optevent_effective_contact_group": "ops"},
        id="contact group of the rule",
    ),
    pytest.param(
        "hostsgroups_having_problems",
        {"hostgroup_num_hosts_down": 2, "hostgroup_num_services_crit": 0},
        [],
        {"hostgroups_having_hosts_down": "on"},
        id="host group problems",
    ),
    pytest.param(
        "servicegroupname",
        {"servicegroup_name": "web"},
        [],
        {"servicegroup_name": "web"},
        id="service group (enforced)",
    ),
    pytest.param(
        "host_labels",
        _HOST_ROW,
        ["cmk/os_family"],
        {
            "host_labels_count": "1",
            "host_labels_1_vs_count": "1",
            "host_labels_1_bool": "and",
            "host_labels_indexof_1": "1",
            "host_labels_1_vs_1_bool": "and",
            "host_labels_1_vs_1_vs": "cmk/os_family:linux",
            "host_labels_1_vs_indexof_1": "1",
        },
        id="host label",
    ),
    pytest.param(
        "svcstate",
        {"service_description": "CPU load", "service_state": 2, "service_has_been_checked": 1},
        [],
        {"st2": "on"},
        id="service state",
    ),
    pytest.param(
        "service_labels",
        {"service_labels": {"app": "web"}},
        ["app"],
        {
            "service_labels_count": "1",
            "service_labels_1_vs_count": "1",
            "service_labels_1_bool": "and",
            "service_labels_indexof_1": "1",
            "service_labels_1_vs_1_bool": "and",
            "service_labels_1_vs_1_vs": "app:web",
            "service_labels_1_vs_indexof_1": "1",
        },
        id="service label",
    ),
    pytest.param(
        "service_tags",
        {"service_tags": {"tier": "gold"}},
        ["tier"],
        {"service_tag_0_grp": "tier", "service_tag_0_op": "is", "service_tag_0_val": "gold"},
        id="service tag",
    ),
    pytest.param("log_class", {"log_class": 1}, [], {"logclass1": "on"}, id="log entry class"),
    pytest.param(
        "log_contact_name",
        {"log_contact_name": "alice"},
        [],
        {"log_contact_name": "alice"},
        id="single log contact",
    ),
    pytest.param(
        "aggr_effective_state",
        {"aggr_effective_state": {"state": 1, "output": ""}},
        [],
        {"bies_filled": "1", "bies1": "on"},
        id="effective aggregation state",
    ),
    pytest.param("event_state", {"event_state": 2}, [], {"event_state_2": "on"}, id="event state"),
    pytest.param(
        "event_phase", {"event_phase": "open"}, [], {"event_phase_open": "on"}, id="event phase"
    ),
    pytest.param(
        "optevent_effective_contactgroup",
        {
            "event_contact_groups_precedence": "host",
            "event_contact_groups": ["ops"],
            "host_contact_groups": ["linux"],
        },
        [],
        {"optevent_effective_contact_group": "linux"},
        id="contact group of the host",
    ),
    pytest.param(
        "hostgroup",
        {"hostgroup_name": "linux"},
        [],
        {"hostgroup": "linux"},
        id="host group (exact match)",
    ),
    pytest.param(
        "service", {"service_description": "CPU load"}, [], {"service": "CPU load"}, id="service"
    ),
    pytest.param(
        "optservicegroup",
        {"service_groups": ["web"]},
        [],
        {"optservice_group": "web"},
        id="service group",
    ),
    pytest.param("customer", {"customer_id": "acme"}, [], {"customer": "acme"}, id="customer"),
    pytest.param(
        "aggr_name",
        {"aggr_name": "Host web01"},
        [],
        {"aggr_name": "Host web01"},
        id="aggregation name",
    ),
    pytest.param(
        "aggr_group", {"aggr_group": "Hosts"}, [], {"aggr_group": "Hosts"}, id="aggregation group"
    ),
    pytest.param("event_id", {"event_id": 42}, [], {"event_id": "42"}, id="event id"),
    pytest.param(
        "event_host", {"event_host": "web01"}, [], {"event_host": "web01"}, id="event host"
    ),
    pytest.param(
        "event_rule_id", {"event_rule_id": "r1"}, [], {"event_rule_id": "r1"}, id="event rule"
    ),
    pytest.param(
        "event_priority", {"event_priority": 3}, [], {"event_priority_3": "on"}, id="event priority"
    ),
    pytest.param(
        "history_what", {"history_what": "NEW"}, [], {"history_what_NEW": "on"}, id="history action"
    ),
    pytest.param(
        "servicegroup",
        {"servicegroup_name": "web"},
        [],
        {"servicegroup": "web"},
        id="service group (exact match)",
    ),
]


@pytest.mark.parametrize("filter_name, row, keys, expected", _VALUED_CASES)
def test_row_filters_value_the_filter_from_the_row(
    filter_name: FilterName,
    row: RowValues,
    keys: Sequence[str],
    expected: FilterHTTPVariables,
) -> None:
    assert ROW_FILTERS[filter_name].variables(row, keys) == expected


def test_row_filters_combine_label_keys_in_one_group() -> None:
    variables = ROW_FILTERS["host_labels"].variables(_HOST_ROW, ["cmk/os_family", "env"])

    assert variables is not None
    assert (variables["host_labels_1_vs_1_vs"], variables["host_labels_1_vs_2_vs"]) == (
        "cmk/os_family:linux",
        "env:prod",
    )


@pytest.mark.parametrize(
    "filter_name, row, keys",
    [
        pytest.param("host_labels", _HOST_ROW, ["cmk/kubernetes"], id="label key not on the host"),
        pytest.param("host_tags", _HOST_ROW, ["address_family"], id="tag group not on the host"),
        pytest.param("host_auxtags", _HOST_ROW, ["snmp"], id="aux tag not on the host"),
        pytest.param("host_labels", _HOST_ROW, [], id="label filter without a key"),
        pytest.param("host_tags", _HOST_ROW, [], id="tag filter without a key"),
        pytest.param("host_auxtags", _HOST_ROW, [], id="aux tag filter without a key"),
        pytest.param(
            "opthostgroup", {"host_groups": ["linux", "web"]}, [], id="several host groups"
        ),
        pytest.param("opthostgroup", {"host_groups": []}, [], id="no host group"),
        pytest.param(
            "log_contact_name", {"log_contact_name": "alice,bob"}, [], id="several contacts"
        ),
        pytest.param(
            "hostsgroups_having_problems",
            {"hostgroup_num_hosts_down": 0},
            [],
            id="host group without problems",
        ),
        pytest.param("aggr_state", {"aggr_state": None}, [], id="aggregation without state"),
        pytest.param("host", {"site": "heute"}, [], id="column not in the row"),
        pytest.param(
            "svcstate",
            {"service_description": "", "service_state": 0, "service_has_been_checked": 0},
            [],
            id="service of a host row",
        ),
        pytest.param("service", {"service_description": ""}, [], id="empty service"),
    ],
)
def test_row_filters_drop_a_filter_the_row_has_no_value_for(
    filter_name: FilterName, row: RowValues, keys: Sequence[str]
) -> None:
    assert ROW_FILTERS[filter_name].variables(row, keys) is None


def test_row_filters_each_have_a_valued_case() -> None:
    assert {case.values[0] for case in _VALUED_CASES} == set(ROW_FILTERS)


@pytest.mark.parametrize(
    "filter_name, row, keys", [pytest.param(*case.values[:3], id=case.id) for case in _VALUED_CASES]
)
def test_row_filters_set_only_variables_the_filter_reads(
    filter_name: FilterName, row: RowValues, keys: Sequence[str]
) -> None:
    if filter_name not in filter_registry:
        pytest.skip(f"This edition registers no filter {filter_name}")
    variables = ROW_FILTERS[filter_name].variables(row, keys)
    filter_variables = set(filter_registry[filter_name].htmlvars)

    assert variables is not None
    if filter_name in _REGISTERING_ONLY_THE_COUNT:
        assert set(variables) & filter_variables
    else:
        assert set(variables) <= filter_variables


def test_row_filters_name_registered_filters() -> None:
    # Only an edition's own filter may be missing; any other gap is a misspelled name.
    assert set(ROW_FILTERS) - set(filter_registry) <= {"customer"}


@pytest.mark.usefixtures("request_context")
def test_drilldown_filters_offer_a_dashboard_only_host_filters() -> None:
    assert drilldown_filters(data_source_registry["hosts"](), "dashboards") == [
        "siteopt",
        "wato_folder",
        "host",
        "hoststate",
        "opthostgroup",
        "host_labels",
        "host_tags",
        "host_auxtags",
    ]


@pytest.mark.usefixtures("request_context")
def test_drilldown_filters_offer_no_folder_without_setup(set_config: SetConfig) -> None:
    with set_config(wato_enabled=False):
        filters = drilldown_filters(data_source_registry["hosts"](), "views")

    assert "wato_folder" not in filters


@pytest.mark.usefixtures("request_context")
def test_drilldown_filters_offer_event_filters_to_a_view_only() -> None:
    data_source = data_source_registry["mkeventd_events"]()

    assert "event_state" in drilldown_filters(data_source, "views")
    assert "event_state" not in drilldown_filters(data_source, "dashboards")
    assert "host" in drilldown_filters(data_source, "dashboards")


@pytest.mark.usefixtures("request_context")
def test_drilldown_filters_offer_no_log_filter_on_a_stats_query() -> None:
    filters = drilldown_filters(data_source_registry["alert_stats"](), "views")

    assert "log_state" not in filters
    assert "host" in filters


@pytest.mark.usefixtures("request_context")
def test_drilldown_filters_offer_only_group_filters_on_a_group_view() -> None:
    assert drilldown_filters(data_source_registry["hostgroups"](), "views") == [
        "hostgroup",
        "hostsgroups_having_problems",
    ]
