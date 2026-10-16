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
    SiteChoiceCondition,
    StateChoiceCondition,
    StringCondition,
)
from cmk.gui.monitor.hosts.context_filters import HostContextFilters
from cmk.gui.type_defs import VisualContext

pytestmark = pytest.mark.usefixtures("request_context")


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
        pytest.param(
            {"siteopt": {"site": "NO_SITE"}},
            SiteChoiceCondition(type="condition", field="site_id", op="one_of", value=[SiteId("NO_SITE")]),
            id="site",
        ),
        pytest.param(
            {"sites": {"sites": "gone|NO_SITE"}, "siteopt": {"site": "other"}},
            SiteChoiceCondition(type="condition", field="site_id", op="one_of", value=[SiteId("gone"), SiteId("NO_SITE")]),
            id="sites over site",
        ),
    ],
)
# fmt: on
def test_a_dashboard_filter_becomes_its_monitoring_page_condition(
    context: VisualContext, expected: FilterNode
) -> None:
    translation = HostContextFilters.translate(context)

    assert translation.node == expected


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
    translation = HostContextFilters.translate(context)

    assert (translation.node, translation.unapplied) == (None, [])


def test_several_dashboard_filters_must_all_match() -> None:
    translation = HostContextFilters.translate(
        {
            "hostregex": {"host_regex": "web"},
            "host_acknowledged": {"is_host_acknowledged": "1"},
        }
    )

    assert translation.node == AndNode(
        type="and",
        children=[
            StringCondition(type="condition", field="name", op="contains", value="web"),
            BooleanCondition(type="condition", field="acknowledged", op="eq", value=True),
        ],
    )


@pytest.mark.parametrize(
    "context",
    [
        pytest.param({"hostgroups": {"hostgroups": "linux"}}, id="no equivalent"),
        pytest.param({"host_ctc": {"host_ctc": "adm*"}}, id="contact pattern"),
        pytest.param({"hostregex": {"host_regex": "web\nGET status"}}, id="line break"),
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
    translation = HostContextFilters.translate(context)

    assert (translation.node, translation.unapplied) == (None, list(context))
