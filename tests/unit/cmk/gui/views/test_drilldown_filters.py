#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.gui.data_source import data_source_registry
from cmk.gui.http import request
from cmk.gui.type_defs import FilterHTTPVariables, FilterName
from cmk.gui.utils.labels import parse_label_groups_from_http_vars
from cmk.gui.views.drilldown_filters import (
    drilldown_filters,
    Dropped,
    dropped_filters_variable,
    dropped_filters_warning,
    row_drilldown,
)
from cmk.gui.visuals.filter import filter_registry
from cmk.gui.visuals.filter.drilldowns import (
    AuxTagKey,
    Drilldown,
    FilterKey,
    LabelKey,
    RowValues,
    TagGroupKey,
)
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

_OTHER_HOST_ROW: RowValues = {
    "site": "stable",
    "host_name": "win01",
    "host_state": 0,
    "host_has_been_checked": 1,
    "host_filename": "/wato/servers/windows/hosts.mk",
    "host_groups": ["windows"],
    "host_labels": {"cmk/os_family": "windows", "env": "prod"},
}

_MAIN_FOLDER_ROW: RowValues = {"host_filename": "/wato/hosts.mk"}

_ALERT_COUNTS: RowValues = {
    "log_alerts_ok": 0,
    "log_alerts_warn": 0,
    "log_alerts_crit": 0,
    "log_alerts_unknown": 0,
}


_REGISTERING_ONLY_THE_COUNT = {"host_labels", "service_labels"}

# The filters only some editions register; any other unregistered name is a misspelling.
_EDITION_ONLY_FILTERS = {
    "customer",
    "azure_resource_group",
    "azure_subscription_name",
    "azure_subscription",
}


def _drilldown(filter_name: FilterName) -> Drilldown:
    if (filter_ := filter_registry.get(filter_name)) is None:
        if filter_name not in _EDITION_ONLY_FILTERS:
            pytest.fail(f"No filter is registered as {filter_name}")
        pytest.skip(f"This edition registers no filter {filter_name}")
    assert filter_.drilldown is not None
    return filter_.drilldown


_VALUED_CASES = [
    pytest.param("siteopt", _HOST_ROW, [], {"site": "heute"}, id="site"),
    pytest.param("site", _HOST_ROW, [], {"site": "heute"}, id="site (enforced)"),
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
        "opthostgroup",
        {"host_groups": ["web", "linux"]},
        [],
        {"opthost_group": "linux|web"},
        id="any of the host groups",
    ),
    pytest.param(
        "opthostgroup",
        {"host_groups": ["all", "linux"]},
        [],
        {"opthost_group": "all|linux"},
        id="host group named all stays",
    ),
    pytest.param("sites", _HOST_ROW, [], {"sites": "heute"}, id="sites"),
    pytest.param("wato_folders", _HOST_ROW, [], {"wato_folders": "servers/linux"}, id="folders"),
    pytest.param(
        "hostgroups",
        {"host_groups": ["linux", "web"]},
        [],
        {"hostgroups": "linux|web"},
        id="several host groups",
    ),
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
        "host_check_command_exact",
        {"host_check_command": "check-mk-host-ping!-w 200.00,80.00%"},
        [],
        {"host_check_command_exact": "check-mk-host-ping"},
        id="host check command without its arguments",
    ),
    pytest.param(
        "host_ctc", {"host_contacts": ["alice"]}, [], {"host_ctc": "alice"}, id="host contact"
    ),
    pytest.param(
        "opthost_contactgroup",
        {"host_contact_groups": ["ops"]},
        [],
        {"opthost_contact_group": "ops"},
        id="host contact group",
    ),
    pytest.param(
        "opthost_contactgroup",
        {"host_contact_groups": ["all", "ops"]},
        [],
        {"opthost_contact_group": "ops"},
        id="host contact group besides all",
    ),
    pytest.param(
        "opthost_contactgroup",
        {"host_contact_groups": ["all", "web", "ops"]},
        [],
        {"opthost_contact_group": "ops|web"},
        id="any of the host contact groups besides all",
    ),
    pytest.param(
        "opthost_contactgroup",
        {"host_contact_groups": ["all"]},
        [],
        {"opthost_contact_group": "all"},
        id="host contact group all alone",
    ),
    pytest.param(
        "host_address",
        {"host_address": "10.0.0.1"},
        [],
        {"host_address": "10.0.0.1", "host_address_prefix": "no"},
        id="primary address",
    ),
    pytest.param(
        "host_ipv4_address",
        {"host_custom_variables": {"ADDRESS_4": "10.0.0.1"}},
        [],
        {"host_ipv4_address": "10.0.0.1", "host_ipv4_address_prefix": "no"},
        id="IPv4 address",
    ),
    pytest.param(
        "host_ipv6_address",
        {"host_custom_variables": {"ADDRESS_6": "fe80::1"}},
        [],
        {"host_ipv6_address": "fe80::1", "host_ipv6_address_prefix": "no"},
        id="IPv6 address",
    ),
    pytest.param(
        "hst_service_level",
        {"host_custom_variables": {"EC_SL": "10"}},
        [],
        {"hst_service_level_lower": "10", "hst_service_level_upper": "10"},
        id="host service level",
    ),
    *(
        pytest.param(
            f"kubernetes_{name}",
            {"host_labels": {f"cmk/kubernetes/{name}": "k"}},
            [],
            {f"kubernetes_{name}": "k"},
            id=f"Kubernetes {name}",
        )
        for name in ("cluster", "namespace", "node", "deployment", "daemonset", "statefulset")
    ),
    *(
        pytest.param(
            f"azure_{name}",
            {"host_labels": {f"cmk/azure/{name}": "a"}},
            [],
            {f"azure_{name}": "a"},
            id=f"Azure {name}",
        )
        for name in ("resource_group", "subscription_name", "subscription")
    ),
    pytest.param(
        "svchardstate",
        {
            "service_description": "CPU load",
            "service_state": 0,
            "service_last_hard_state": 2,
            "service_has_been_checked": 1,
        },
        [],
        {"hdst2": "on"},
        id="service hard state",
    ),
    pytest.param(
        "service_state_type",
        {"service_description": "CPU load", "service_state_type": 0},
        [],
        {"is_service_state_type": "0"},
        id="service state type",
    ),
    pytest.param(
        "service_staleness",
        {"service_description": "CPU load", "service_staleness": 2.5},
        [],
        {"is_service_staleness": "1"},
        id="stale service",
    ),
    pytest.param(
        "check_command_exact",
        {"service_check_command": "check_mk-cpu_loads"},
        [],
        {"check_command_exact": "check_mk-cpu_loads"},
        id="service check command",
    ),
    pytest.param(
        "service_ctc",
        {"service_contacts": ["alice"]},
        [],
        {"service_ctc": "alice"},
        id="service contact",
    ),
    pytest.param(
        "optservice_contactgroup",
        {"service_contact_groups": ["ops"]},
        [],
        {"optservice_contact_group": "ops"},
        id="service contact group",
    ),
    pytest.param(
        "optservice_contactgroup",
        {"service_contact_groups": ["all", "ops"]},
        [],
        {"optservice_contact_group": "ops"},
        id="service contact group besides all",
    ),
    pytest.param(
        "svc_service_level",
        {"service_custom_variables": {"EC_SL": "20"}},
        [],
        {"svc_service_level_lower": "20", "svc_service_level_upper": "20"},
        id="service service level",
    ),
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
    pytest.param(
        "optservicegroup",
        {"service_groups": ["web", "db"]},
        [],
        {"optservice_group": "db|web"},
        id="any of the service groups",
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


@pytest.mark.usefixtures("request_context")
@pytest.mark.parametrize("filter_name, row, keys, expected", _VALUED_CASES)
def test_drilldowns_value_the_filter_from_the_row(
    filter_name: FilterName,
    row: RowValues,
    keys: Sequence[str],
    expected: FilterHTTPVariables,
) -> None:
    assert _drilldown(filter_name).variables(row, keys) == expected


def test_drilldowns_combine_label_keys_in_one_group() -> None:
    variables = _drilldown("host_labels").variables(_HOST_ROW, ["cmk/os_family", "env"])

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
        pytest.param("host_ctc", {"host_contacts": ["alice", "bob"]}, [], id="several contacts"),
        pytest.param("hst_service_level", {"host_custom_variables": {}}, [], id="no service level"),
        pytest.param(
            "kubernetes_cluster", {"host_labels": {"env": "prod"}}, [], id="no Kubernetes label"
        ),
        pytest.param(
            "service_staleness",
            {"service_description": "", "service_staleness": 0.0},
            [],
            id="staleness of a host row",
        ),
    ],
)
def test_drilldowns_drop_a_filter_the_row_has_no_value_for(
    filter_name: FilterName, row: RowValues, keys: Sequence[str]
) -> None:
    assert _drilldown(filter_name).variables(row, keys) is None


@pytest.mark.parametrize(
    "filter_name, key",
    [
        pytest.param("host_labels", LabelKey("host"), id="host label"),
        pytest.param("service_labels", LabelKey("service"), id="service label"),
        pytest.param("host_tags", TagGroupKey(), id="host tag"),
        pytest.param("service_tags", TagGroupKey(), id="service tag"),
        pytest.param("host_auxtags", AuxTagKey(max_count=3), id="aux tag"),
        pytest.param("host", None, id="unkeyed"),
    ],
)
def test_drilldowns_name_the_key_a_filter_takes(
    filter_name: FilterName, key: FilterKey | None
) -> None:
    assert _drilldown(filter_name).key == key


def test_drilldowns_carry_the_keys_the_row_has_and_name_the_others() -> None:
    row = {"host_tags": {"ip-v4": "ip-v4", "checkmk-agent": "checkmk-agent"}}

    assert _drilldown("host_auxtags").carried([row], ["ip-v4", "ip-v6", "checkmk-agent"]) == (
        {"host_auxtags_0": "ip-v4", "host_auxtags_1": "checkmk-agent"},
        ["ip-v6"],
    )


def test_drilldowns_carry_nothing_when_the_row_has_none_of_the_keys() -> None:
    assert _drilldown("host_auxtags").carried([{"host_tags": {}}], ["ip-v6"]) == (None, ["ip-v6"])


@pytest.mark.parametrize(
    "filter_name, expected",
    [
        pytest.param("sites", {"sites": "heute|stable"}, id="sites"),
        pytest.param(
            "wato_folders", {"wato_folders": "servers/linux|servers/windows"}, id="folders"
        ),
        pytest.param("hostgroups", {"hostgroups": "linux|windows"}, id="host groups"),
        pytest.param("hoststate", {"hst0": "on", "hst1": "on"}, id="host states"),
    ],
)
def test_drilldowns_merge_the_values_of_several_rows(
    filter_name: FilterName, expected: FilterHTTPVariables
) -> None:
    assert _drilldown(filter_name).carried([_HOST_ROW, _OTHER_HOST_ROW], []) == (expected, [])


def test_drilldowns_merge_folders_leaving_out_the_main_folder() -> None:
    assert _drilldown("wato_folders").carried([_HOST_ROW, _MAIN_FOLDER_ROW], []) == (
        {"wato_folders": "servers/linux"},
        [],
    )


def test_drilldowns_carry_no_folder_for_a_host_in_the_main_folder() -> None:
    assert _drilldown("wato_folders").carried([_MAIN_FOLDER_ROW], []) == (None, [])


def test_drilldowns_merge_the_labels_of_several_rows_into_any_of_their_values() -> None:
    variables, missing = _drilldown("host_labels").carried(
        [_HOST_ROW, _OTHER_HOST_ROW], ["cmk/os_family"]
    )

    assert variables is not None
    assert parse_label_groups_from_http_vars("host_labels", variables) == [
        ("and", [("and", "cmk/os_family:linux"), ("or", "cmk/os_family:windows")])
    ]
    assert missing == []


def test_drilldowns_drop_a_single_value_filter_for_several_rows() -> None:
    assert _drilldown("siteopt").carried([_HOST_ROW, _OTHER_HOST_ROW], []) == (None, [])


def test_drilldowns_each_have_a_valued_case() -> None:
    assert {
        filter_name
        for filter_name, filter_ in filter_registry.items()
        if filter_.drilldown is not None
    } <= {case.values[0] for case in _VALUED_CASES}


@pytest.mark.usefixtures("request_context")
@pytest.mark.parametrize(
    "filter_name, row, keys", [pytest.param(*case.values[:3], id=case.id) for case in _VALUED_CASES]
)
def test_drilldowns_set_only_variables_the_filter_reads(
    filter_name: FilterName, row: RowValues, keys: Sequence[str]
) -> None:
    variables = _drilldown(filter_name).variables(row, keys)
    filter_variables = set(filter_registry[filter_name].htmlvars)

    assert variables is not None
    if filter_name in _REGISTERING_ONLY_THE_COUNT:
        assert set(variables) & filter_variables
    else:
        assert set(variables) <= filter_variables


@pytest.mark.usefixtures("request_context")
def test_drilldown_filters_offer_a_dashboard_only_host_and_service_filters() -> None:
    assert drilldown_filters(data_source_registry["hosts"](), "dashboards") == [
        "wato_folder",
        "host",
        "host_ipv4_address",
        "host_ipv6_address",
        "host_address",
        "opthostgroup",
        "opthost_contactgroup",
        "host_ctc",
        "host_check_command_exact",
        "hoststate",
        "service",
        "optservicegroup",
        "optservice_contactgroup",
        "service_ctc",
        "check_command_exact",
        "svcstate",
        "svchardstate",
        "service_state_type",
        "service_staleness",
        "host_labels",
        "service_labels",
        "host_auxtags",
        "host_tags",
        "service_tags",
        "hst_service_level",
        "svc_service_level",
        "siteopt",
        "site",
        "kubernetes_cluster",
        "kubernetes_daemonset",
        "kubernetes_deployment",
        "kubernetes_namespace",
        "kubernetes_node",
        "kubernetes_statefulset",
    ]


@pytest.mark.usefixtures("request_context")
def test_drilldown_filters_offer_no_host_filter_that_reads_a_service_column() -> None:
    filters = drilldown_filters(data_source_registry["services"](), "views")

    assert {"host_state_type", "address_family", "address_families"}.isdisjoint(filters)
    assert "service_state_type" in filters


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
def test_drilldown_filters_offer_alert_statistics_the_class_and_the_alert_types() -> None:
    filters = drilldown_filters(data_source_registry["alert_stats"](), "views")

    assert {name for name in filters if filter_registry[name].info == "log"} == {
        "log_class",
        "log_state",
    }


@pytest.mark.parametrize(
    "row, expected",
    [
        pytest.param(
            {
                **_ALERT_COUNTS,
                "service_description": "CPU load",
                "log_alerts_ok": 2,
                "log_alerts_crit": 1,
            },
            {"logst_s0": "on", "logst_s2": "on"},
            id="service row",
        ),
        pytest.param(
            {**_ALERT_COUNTS, "service_description": "", "log_alerts_warn": 1},
            {"logst_h1": "on"},
            id="host row",
        ),
        pytest.param(
            {**_ALERT_COUNTS, "service_description": "CPU load"}, None, id="row without alerts"
        ),
    ],
)
@pytest.mark.usefixtures("request_context")
def test_row_drilldown_values_the_alert_types_of_alert_statistics_from_the_counts(
    row: RowValues, expected: FilterHTTPVariables | None
) -> None:
    drilldown = row_drilldown(data_source_registry["alert_stats"](), "log_state")

    assert drilldown is not None
    assert drilldown.variables(row, []) == expected


@pytest.mark.usefixtures("request_context")
def test_row_drilldown_values_the_class_of_alert_statistics_as_alerts() -> None:
    drilldown = row_drilldown(data_source_registry["alert_stats"](), "log_class")

    assert drilldown is not None
    assert drilldown.variables({}, []) == {"logclass1": "on"}


@pytest.mark.usefixtures("request_context")
@pytest.mark.parametrize("filter_name", ["log_class", "log_state"])
def test_row_drilldown_sets_only_variables_the_alert_statistics_filter_reads(
    filter_name: FilterName,
) -> None:
    drilldown = row_drilldown(data_source_registry["alert_stats"](), filter_name)
    assert drilldown is not None
    row: RowValues = {**_ALERT_COUNTS, "service_description": "CPU load", "log_alerts_crit": 1}

    variables = drilldown.variables(row, [])

    assert variables is not None
    assert set(variables) <= set(filter_registry[filter_name].htmlvars)


@pytest.mark.usefixtures("request_context")
def test_drilldown_filters_offer_a_group_view_only_group_host_and_service_filters() -> None:
    filters = drilldown_filters(data_source_registry["hostgroups"](), "views")

    assert {filter_registry[name].info for name in filters} == {"hostgroup", "host", "service"}


@pytest.mark.usefixtures("request_context")
@pytest.mark.parametrize(
    "datasource, filters",
    [
        pytest.param("bi_aggregations", {"host", "service"}, id="BI view"),
        pytest.param("hosts", {"service"}, id="host view"),
    ],
)
def test_drilldown_filters_offer_host_and_service_filters_without_their_info(
    datasource: str, filters: set[FilterName]
) -> None:
    assert filters <= set(drilldown_filters(data_source_registry[datasource](), "views"))


@pytest.mark.usefixtures("request_context")
def test_dropped_filters_warning_names_each_filter_and_why() -> None:
    request.set_var(
        "_dropped_filters",
        dropped_filters_variable(
            [Dropped("host_labels", "no_such_key", "env"), Dropped("opthostgroup", "no_value")]
        ),
    )

    assert dropped_filters_warning(request) == (
        "These filters could not be carried over, so this page shows a wider scope than the "
        f"clicked object: {filter_registry['host_labels'].title} (env): the clicked object lacks "
        f"the configured key; {filter_registry['opthostgroup'].title}: the clicked object has no "
        "value for it"
    )


@pytest.mark.usefixtures("request_context")
def test_dropped_filters_warning_names_a_filter_this_edition_lacks_by_its_id() -> None:
    request.set_var("_dropped_filters", "no_such_filter:not_available")

    assert dropped_filters_warning(request) == (
        "These filters could not be carried over, so this page shows a wider scope than the "
        "clicked object: no_such_filter: it is not available here"
    )


@pytest.mark.usefixtures("request_context")
def test_dropped_filters_warning_ignores_an_unknown_reason() -> None:
    request.set_var("_dropped_filters", "host_labels:no_reason")

    assert dropped_filters_warning(request) is None


@pytest.mark.usefixtures("request_context")
def test_dropped_filters_warning_ignores_a_name_that_is_no_filter_id() -> None:
    request.set_var("_dropped_filters", "<b>Call support</b>:no_value")

    assert dropped_filters_warning(request) is None


@pytest.mark.usefixtures("request_context")
def test_dropped_filters_warning_ignores_a_key_with_markup() -> None:
    request.set_var("_dropped_filters", "host_labels:no_such_key:<b>Call support</b>")

    assert dropped_filters_warning(request) is None
