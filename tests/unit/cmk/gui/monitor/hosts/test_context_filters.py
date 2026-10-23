#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime, UTC

import pytest
import time_machine

from cmk.ccc.site import SiteId
from cmk.gui.monitor.hosts._api._filters import SiteScopedFilter
from cmk.gui.monitor.hosts.context_filters import translate_filters
from cmk.gui.monitor.shared import (
    AndNode,
    BooleanCondition,
    FilterNode,
    LabelChoiceCondition,
    NameChoiceCondition,
    NotNode,
    NumericCondition,
    OrNode,
    StateChoiceCondition,
    StringCondition,
    TimestampCondition,
)
from cmk.gui.type_defs import FilterHTTPVariables, VisualContext


# fmt: off
@pytest.mark.parametrize(
    "context, expected",
    [
        pytest.param(
            {"hostregex": {"host_regex": "web"}},
            StringCondition(type="condition", field="name", op="contains", value="web"),
            id="host name regex",
        ),
        pytest.param(
            {"host": {"host": "web-01"}},
            StringCondition(type="condition", field="name", op="matches", value="^web\\-01$"),
            id="exact host name",
        ),
        pytest.param(
            {"hostregex": {"host_regex": "web", "neg_host_regex": "on"}},
            NotNode(type="not", child=StringCondition(type="condition", field="name", op="contains", value="web")),
            id="negated host name regex",
        ),
        pytest.param(
            {"hostalias": {"hostalias": "Web"}},
            StringCondition(type="condition", field="alias", op="contains", value="Web"),
            id="host alias",
        ),
        pytest.param(
            {"address_family": {"address_family": "4"}},
            LabelChoiceCondition(type="condition", field="tags", op="all_of", value=["address_family:ip-v4-only"]),
            id="address family",
        ),
        pytest.param(
            {"address_families": {"address_families": "4_only"}},
            AndNode(type="and", children=[
                LabelChoiceCondition(type="condition", field="tags", op="all_of", value=["ip-v4:ip-v4"]),
                NotNode(type="not", child=LabelChoiceCondition(type="condition", field="tags", op="all_of", value=["ip-v6:ip-v6"])),
            ]),
            id="address families with IPv4 only",
        ),
        pytest.param(
            {"host_auxtags": {"host_auxtags_0": "snmp"}},
            LabelChoiceCondition(type="condition", field="tags", op="all_of", value=["snmp:snmp"]),
            id="auxiliary tag",
        ),
        pytest.param(
            {
                "host_labels": {
                    "host_labels_count": "1",
                    "host_labels_1_vs_count": "2",
                    "host_labels_1_bool": "and",
                    "host_labels_1_vs_1_bool": "and",
                    "host_labels_1_vs_1_vs": "cmk/os_family:linux",
                    "host_labels_1_vs_2_bool": "or",
                    "host_labels_1_vs_2_vs": "cmk/os_family:windows",
                }
            },
            OrNode(type="or", children=[
                LabelChoiceCondition(type="condition", field="labels", op="all_of", value=["cmk/os_family:linux"]),
                LabelChoiceCondition(type="condition", field="labels", op="all_of", value=["cmk/os_family:windows"]),
            ]),
            id="host labels",
        ),
        pytest.param(
            {"kubernetes_cluster": {"kubernetes_cluster": "prod:1"}},
            LabelChoiceCondition(type="condition", field="labels", op="all_of", value=["cmk/kubernetes/cluster:prod:1"]),
            id="Kubernetes cluster",
        ),
        pytest.param(
            {"hostnameoralias": {"hostnameoralias": "web"}},
            OrNode(type="or", children=[
                StringCondition(type="condition", field="name", op="contains", value="web"),
                StringCondition(type="condition", field="alias", op="contains", value="web"),
            ]),
            id="host name or alias",
        ),
        pytest.param(
            {"host_address": {"host_address": "10.0.", "host_address_prefix": "yes"}},
            StringCondition(type="condition", field="address", op="matches", value="^10\\.0\\."),
            id="address prefix",
        ),
        pytest.param(
            {"hoststate": {"hst0": "", "hst1": "on", "hst2": "on", "hstp": ""}},
            StateChoiceCondition(type="condition", field="state", op="one_of", value=["DOWN", "UNREACHABLE"]),
            id="host states",
        ),
        pytest.param(
            {"hosts_having_service_problems": {"hosts_having_services_warn": "on", "hosts_having_services_crit": "on"}},
            OrNode(type="or", children=[
                NumericCondition(type="condition", field="num_services_warn", op="gt", value=0),
                NumericCondition(type="condition", field="num_services_crit", op="gt", value=0),
            ]),
            id="hosts having service problems",
        ),
        pytest.param(
            {"host_acknowledged": {"is_host_acknowledged": "1"}},
            BooleanCondition(type="condition", field="acknowledged", op="eq", value=True),
            id="acknowledged",
        ),
        pytest.param(
            {"host_scheduled_downtime_depth": {"is_host_scheduled_downtime_depth": "0"}},
            BooleanCondition(type="condition", field="in_downtime", op="eq", value=False),
            id="not in downtime",
        ),
        pytest.param(
            {"host_staleness": {"is_host_staleness": "1"}},
            BooleanCondition(type="condition", field="stale", op="eq", value=True),
            id="stale",
        ),
        pytest.param(
            {"host_notifications_enabled": {"is_host_notifications_enabled": "1"}},
            BooleanCondition(type="condition", field="notifications_enabled", op="eq", value=True),
            id="notifications enabled",
        ),
        pytest.param(
            {"host_in_notification_period": {"is_host_in_notification_period": "1"}},
            BooleanCondition(type="condition", field="in_notification_period", op="eq", value=True),
            id="in notification period",
        ),
        pytest.param(
            {"host_in_service_period": {"is_host_in_service_period": "1"}},
            BooleanCondition(type="condition", field="in_service_period", op="eq", value=True),
            id="in service period",
        ),
        pytest.param(
            {"host_ctc": {"host_ctc": "admin"}},
            NameChoiceCondition(type="condition", field="contacts", op="one_of", value=["admin"]),
            id="contact",
        ),
        pytest.param(
            {"host_ctc_regex": {"host_ctc_regex": "adm.*"}},
            StringCondition(type="condition", field="contacts", op="contains", value="adm.*"),
            id="contact regex",
        ),
        pytest.param(
            {"opthostgroup": {"opthost_group": "linux|windows"}},
            NameChoiceCondition(type="condition", field="groups", op="one_of", value=["linux", "windows"]),
            id="host groups",
        ),
        pytest.param(
            {"opthost_contactgroup": {"opthost_contact_group": "all|admins"}},
            NameChoiceCondition(type="condition", field="contact_groups", op="one_of", value=["all", "admins"]),
            id="contact groups",
        ),
        pytest.param(
            {"host_num_services": {"host_num_services_from": "1", "host_num_services_until": "9"}},
            AndNode(type="and", children=[
                NumericCondition(type="condition", field="num_services", op="gte", value=1),
                NumericCondition(type="condition", field="num_services", op="lte", value=9),
            ]),
            id="service count range",
        ),
    ],
)
# fmt: on
def test_a_dashboard_filter_becomes_its_monitoring_page_condition(
    context: VisualContext, expected: FilterNode
) -> None:
    translation = translate_filters(context)

    assert translation.filter == SiteScopedFilter(node=expected, sites=None, exclude_sites=False)


@pytest.mark.parametrize(
    "variable, expected",
    [
        pytest.param(
            "hosts_having_services_warn",
            NumericCondition(type="condition", field="num_services_warn", op="gt", value=0),
            id="warn",
        ),
        pytest.param(
            "hosts_having_services_crit",
            NumericCondition(type="condition", field="num_services_crit", op="gt", value=0),
            id="crit",
        ),
        pytest.param(
            "hosts_having_services_pending",
            NumericCondition(type="condition", field="num_services_pending", op="gt", value=0),
            id="pending",
        ),
        pytest.param(
            "hosts_having_services_unknown",
            NumericCondition(type="condition", field="num_services_unknown", op="gt", value=0),
            id="unknown",
        ),
    ],
)
def test_a_dashboard_service_problem_filter_counts_the_services_in_that_state(
    variable: str, expected: FilterNode
) -> None:
    translation = translate_filters({"hosts_having_service_problems": {variable: "on"}})

    assert translation.filter == SiteScopedFilter(node=expected, sites=None, exclude_sites=False)


@pytest.mark.parametrize(
    "obj", ["cluster", "namespace", "node", "deployment", "daemonset", "statefulset"]
)
def test_a_dashboard_kubernetes_filter_becomes_a_condition_on_the_label_of_its_object(
    obj: str,
) -> None:
    translation = translate_filters({f"kubernetes_{obj}": {f"kubernetes_{obj}": "prod"}})

    assert translation.filter == SiteScopedFilter(
        node=LabelChoiceCondition(
            type="condition", field="labels", op="all_of", value=[f"cmk/kubernetes/{obj}:prod"]
        ),
        sites=None,
        exclude_sites=False,
    )


_TAG_GROUPS = frozenset({"criticality", "agent"})


def _tag_row(group: str, operator: str, tag: str) -> FilterHTTPVariables:
    return {"host_tag_0_grp": group, "host_tag_0_op": operator, "host_tag_0_val": tag}


def test_a_dashboard_tag_filter_becomes_a_condition_on_the_tags_of_the_host() -> None:
    translation = translate_filters(
        {"host_tags": _tag_row("criticality", "is", "prod")}, tag_groups=_TAG_GROUPS
    )

    assert translation.filter == SiteScopedFilter(
        node=LabelChoiceCondition(
            type="condition", field="tags", op="all_of", value=["criticality:prod"]
        ),
        sites=None,
        exclude_sites=False,
    )


def test_a_dashboard_tag_filter_of_a_group_that_is_not_configured_is_reported() -> None:
    translation = translate_filters(
        {"host_tags": _tag_row("gone", "is", "prod")}, tag_groups=_TAG_GROUPS
    )

    assert (translation.filter, translation.unapplied) == (None, ["host_tags"])


@pytest.mark.parametrize(
    "context, expected_sites",
    [
        pytest.param({"site": {"site": "NO_SITE"}}, {"NO_SITE"}, id="single site"),
        pytest.param({"siteopt": {"site": "NO_SITE"}}, {"NO_SITE"}, id="site"),
        pytest.param(
            {"sites": {"sites": "gone|NO_SITE"}, "siteopt": {"site": "other"}},
            {"gone", "NO_SITE"},
            id="sites over site",
        ),
    ],
)
def test_a_dashboard_site_filter_scopes_the_sites_to_query(
    context: VisualContext, expected_sites: set[str]
) -> None:
    translation = translate_filters(context)

    assert translation.filter == SiteScopedFilter(
        node=None, sites=frozenset(map(SiteId, expected_sites)), exclude_sites=False
    )


def test_a_dashboard_time_filter_becomes_timestamp_bounds_from_the_time_of_the_translation() -> None:
    now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

    with time_machine.travel(now, tick=False):
        translation = translate_filters(
            {
                "host_last_check": {
                    "host_last_check_from": "2",
                    "host_last_check_from_range": "3600",
                },
                "host_last_state_change": {
                    "host_last_state_change_until": "1",
                    "host_last_state_change_until_range": "86400",
                },
            }
        )

    assert translation.filter == SiteScopedFilter(
        node=AndNode(
            type="and",
            children=[
                TimestampCondition(
                    type="condition",
                    field="last_check",
                    op="gte",
                    value=int(now.timestamp()) - 2 * 3600,
                ),
                TimestampCondition(
                    type="condition",
                    field="last_state_change",
                    op="lte",
                    value=int(now.timestamp()) - 86400,
                ),
            ],
        ),
        sites=None,
        exclude_sites=False,
    )


def test_several_dashboard_filters_must_all_match() -> None:
    translation = translate_filters(
        {
            "hostregex": {"host_regex": "web"},
            "host_acknowledged": {"is_host_acknowledged": "1"},
        }
    )

    assert translation.filter == SiteScopedFilter(
        node=AndNode(
            type="and",
            children=[
                StringCondition(type="condition", field="name", op="contains", value="web"),
                BooleanCondition(type="condition", field="acknowledged", op="eq", value=True),
            ],
        ),
        sites=None,
        exclude_sites=False,
    )


@pytest.mark.parametrize(
    "context",
    [
        pytest.param({"hostregex": {"host_regex": "web\nGET status"}}, id="line break"),
        pytest.param(
            {"opthost_contactgroup": {"opthost_contact_group": "all|adm\nGET status"}},
            id="line break in a contact group",
        ),
        pytest.param(
            {
                "host_labels": {
                    "host_labels_count": "1",
                    "host_labels_1_vs_count": "1",
                    "host_labels_1_vs_1_vs": "a:1\nGET status",
                }
            },
            id="line break in a label",
        ),
    ],
)
def test_a_dashboard_filter_the_table_cannot_apply_is_reported(context: VisualContext) -> None:
    translation = translate_filters(context)

    assert (translation.filter, translation.unapplied) == (None, list(context))
