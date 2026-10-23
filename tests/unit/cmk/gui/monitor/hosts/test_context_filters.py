#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.site import SiteId
from cmk.gui.monitor.hosts._api._filters import (
    AndNode,
    BooleanCondition,
    FilterNode,
    NameChoiceCondition,
    NotNode,
    NumericCondition,
    OrNode,
    SiteScopedFilter,
    StateChoiceCondition,
    StringCondition,
)
from cmk.gui.monitor.hosts.context_filters import translate_filters
from cmk.gui.type_defs import VisualContext


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
            {"hostregex": {"host_regex": "web.*(01|02)"}},
            StringCondition(type="condition", field="name", op="contains", value="web.*(01|02)"),
            id="host name regex passed on verbatim",
        ),
        pytest.param(
            {"host": {"host": "web-01", "neg_host": "on"}},
            NotNode(type="not", child=StringCondition(type="condition", field="name", op="matches", value="^web\\-01$")),
            id="negated exact host name",
        ),
        pytest.param(
            {"hostalias": {"hostalias": "Web"}},
            StringCondition(type="condition", field="alias", op="contains", value="Web"),
            id="host alias",
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
            {"opthost_contactgroup": {"opthost_contact_group": "all", "neg_opthost_contact_group": "on"}},
            NotNode(type="not", child=NameChoiceCondition(type="condition", field="contact_groups", op="one_of", value=["all"])),
            id="negated contact groups",
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


@pytest.mark.parametrize(
    "context",
    [
        pytest.param({"hostregex": {"host_regex": ""}}, id="empty text"),
        pytest.param({"sites": {"sites": "|"}}, id="no site picked"),
        pytest.param({"host_acknowledged": {"is_host_acknowledged": "-1"}}, id="ignored flag"),
        pytest.param(
            {"hoststate": {"hst0": "on", "hst1": "on", "hst2": "on", "hstp": "on"}},
            id="every state",
        ),
    ],
)
def test_a_dashboard_filter_that_selects_everything_adds_no_condition(
    context: VisualContext,
) -> None:
    translation = translate_filters(context)

    assert (translation.filter, translation.unapplied) == (None, [])


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
        pytest.param({"hostgroups": {"hostgroups": "linux"}}, id="no equivalent"),
        pytest.param({"host_ctc": {"host_ctc": "adm*"}}, id="contact pattern"),
        pytest.param({"hostregex": {"host_regex": "web\nGET status"}}, id="line break"),
        pytest.param({"sites": {"sites": "a\nb|c"}}, id="line break in a site"),
        pytest.param({"host": {"host": "web\nGET status"}}, id="line break in the exact name"),
        pytest.param(
            {"host_address": {"host_address": "10.0.0.1\nGET status"}},
            id="line break in the address",
        ),
        pytest.param(
            {"opthost_contactgroup": {"opthost_contact_group": "all|adm\nGET status"}},
            id="line break in a contact group",
        ),
        pytest.param({"host_ctc": {"host_ctc": "adm\nGET status"}}, id="line break in a contact"),
        pytest.param({"hostregex": {"host_regex": "web["}}, id="invalid regex"),
        pytest.param({"hostalias": {"hostalias": "(Web"}}, id="invalid alias regex"),
        pytest.param(
            {
                "host_num_services": {
                    "host_num_services_from": "1",
                    "host_num_services_until": "1.5",
                }
            },
            id="service count bound not a number",
        ),
    ],
)
def test_a_dashboard_filter_the_table_cannot_apply_is_reported(context: VisualContext) -> None:
    translation = translate_filters(context)

    assert (translation.filter, translation.unapplied) == (None, list(context))
