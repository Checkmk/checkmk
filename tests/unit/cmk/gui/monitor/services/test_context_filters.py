#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.monitor.services._api._filters import (
    ServiceAndNode,
    ServiceBooleanCondition,
    ServiceFilterNode,
    ServiceNameChoiceCondition,
    ServiceNotNode,
    ServiceStateChoiceCondition,
    ServiceStringCondition,
)
from cmk.gui.monitor.services.context_filters import translate_filters
from cmk.gui.type_defs import VisualContext


# fmt: off
@pytest.mark.parametrize(
    "context, expected",
    [
        pytest.param(
            {"serviceregex": {"service_regex": "CPU"}},
            ServiceStringCondition(type="condition", field="name", op="contains", value="CPU"),
            id="service name regex",
        ),
        pytest.param(
            {"serviceregex": {"service_regex": "CPU", "neg_service_regex": "on"}},
            ServiceNotNode(type="not", child=ServiceStringCondition(type="condition", field="name", op="contains", value="CPU")),
            id="negated service name regex",
        ),
        pytest.param(
            {"service": {"service": "CPU load"}},
            ServiceStringCondition(type="condition", field="name", op="matches", value="^CPU\\ load$"),
            id="exact service name",
        ),
        pytest.param(
            {"output": {"service_output": "timeout"}},
            ServiceStringCondition(type="condition", field="summary", op="contains", value="timeout"),
            id="summary",
        ),
        pytest.param(
            {"output": {"service_output": "timeout", "neg_service_output": "on"}},
            ServiceNotNode(type="not", child=ServiceStringCondition(type="condition", field="summary", op="contains", value="timeout")),
            id="negated summary",
        ),
        pytest.param(
            {"svcstate": {"st0": "", "st1": "on", "st2": "on", "st3": "", "stp": ""}},
            ServiceStateChoiceCondition(type="condition", field="state", op="one_of", value=["WARN", "CRIT"]),
            id="service states",
        ),
        pytest.param(
            {"svcstate": {"st0": "", "st1": "", "st2": "", "st3": "on", "stp": "on"}},
            ServiceStateChoiceCondition(type="condition", field="state", op="one_of", value=["UNKNOWN", "PENDING"]),
            id="unknown and pending",
        ),
        pytest.param(
            {"service_staleness": {"is_service_staleness": "1"}},
            ServiceBooleanCondition(type="condition", field="stale", op="eq", value=True),
            id="stale",
        ),
        pytest.param(
            {"service_acknowledged": {"is_service_acknowledged": "0"}},
            ServiceBooleanCondition(type="condition", field="acknowledged", op="eq", value=False),
            id="not acknowledged",
        ),
        pytest.param(
            {"service_scheduled_downtime_depth": {"is_service_scheduled_downtime_depth": "1"}},
            ServiceBooleanCondition(type="condition", field="in_downtime", op="eq", value=True),
            id="in downtime",
        ),
        pytest.param(
            {"service_is_flapping": {"is_service_is_flapping": "1"}},
            ServiceBooleanCondition(type="condition", field="is_flapping", op="eq", value=True),
            id="flapping",
        ),
        pytest.param(
            {"service_notifications_enabled": {"is_service_notifications_enabled": "0"}},
            ServiceBooleanCondition(type="condition", field="notifications_enabled", op="eq", value=False),
            id="notifications disabled",
        ),
        pytest.param(
            {"service_in_notification_period": {"is_service_in_notification_period": "1"}},
            ServiceBooleanCondition(type="condition", field="in_notification_period", op="eq", value=True),
            id="in notification period",
        ),
        pytest.param(
            {"service_in_service_period": {"is_service_in_service_period": "1"}},
            ServiceBooleanCondition(type="condition", field="in_service_period", op="eq", value=True),
            id="in service period",
        ),
        pytest.param(
            {"service_ctc": {"service_ctc": "admin"}},
            ServiceNameChoiceCondition(type="condition", field="contacts", op="one_of", value=["admin"]),
            id="contact",
        ),
        pytest.param(
            {"service_ctc_regex": {"service_ctc_regex": "adm"}},
            ServiceStringCondition(type="condition", field="contacts", op="contains", value="adm"),
            id="contact regex",
        ),
        pytest.param(
            {"service_ctc_regex": {"service_ctc_regex": "adm", "neg_service_ctc_regex": "on"}},
            ServiceStringCondition(type="condition", field="contacts", op="contains", value="adm"),
            id="contact regex is never negated",
        ),
        pytest.param(
            {"optservice_contactgroup": {"optservice_contact_group": "all|admins"}},
            ServiceNameChoiceCondition(type="condition", field="contact_groups", op="one_of", value=["all", "admins"]),
            id="contact groups",
        ),
        pytest.param(
            {"optservice_contactgroup": {"optservice_contact_group": "all", "neg_optservice_contact_group": "on"}},
            ServiceNotNode(type="not", child=ServiceNameChoiceCondition(type="condition", field="contact_groups", op="one_of", value=["all"])),
            id="negated contact groups",
        ),
        pytest.param(
            {"servicegroups": {"servicegroups": "web|db"}},
            ServiceNameChoiceCondition(type="condition", field="groups", op="one_of", value=["web", "db"]),
            id="service groups",
        ),
        pytest.param(
            {"servicegroups": {"servicegroups": "web", "neg_servicegroups": "on"}},
            ServiceNotNode(type="not", child=ServiceNameChoiceCondition(type="condition", field="groups", op="one_of", value=["web"])),
            id="negated service groups",
        ),
    ],
)
# fmt: on
def test_a_dashboard_filter_becomes_its_monitoring_page_condition(
    context: VisualContext, expected: ServiceFilterNode
) -> None:
    translation = translate_filters(context)

    assert (translation.filter, translation.unapplied) == (expected, [])


@pytest.mark.parametrize(
    "context",
    [
        pytest.param({"serviceregex": {"service_regex": ""}}, id="empty text"),
        pytest.param(
            {"servicegroups": {"servicegroups": "|", "neg_servicegroups": "on"}},
            id="no group excluded",
        ),
        pytest.param({"service_is_flapping": {"is_service_is_flapping": "-1"}}, id="ignored flag"),
        pytest.param(
            {"svcstate": {"st0": "on", "st1": "on", "st2": "on", "st3": "on", "stp": "on"}},
            id="every state",
        ),
        pytest.param(
            {"svcstate": {"st0": "", "st1": "", "st2": "", "st3": "", "stp": ""}},
            id="no state",
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
            "serviceregex": {"service_regex": "CPU"},
            "service_acknowledged": {"is_service_acknowledged": "1"},
        }
    )

    assert translation.filter == ServiceAndNode(
        type="and",
        children=[
            ServiceStringCondition(type="condition", field="name", op="contains", value="CPU"),
            ServiceBooleanCondition(type="condition", field="acknowledged", op="eq", value=True),
        ],
    )


@pytest.mark.parametrize(
    "context",
    [
        pytest.param({"service_display_name": {"service_display_name": "CPU"}}, id="no equivalent"),
        pytest.param({"siteopt": {"site": "NO_SITE"}}, id="site"),
        pytest.param({"servicegroups": {"servicegroups": "web*"}}, id="group pattern"),
        pytest.param({"servicegroups": {"servicegroups": "|"}}, id="no group named"),
        pytest.param({"service_ctc": {"service_ctc": "adm*"}}, id="contact pattern"),
        pytest.param({"serviceregex": {"service_regex": "CPU\nGET status"}}, id="line break"),
        pytest.param({"service": {"service": "CPU\nGET status"}}, id="line break in the exact name"),
        pytest.param(
            {"optservice_contactgroup": {"optservice_contact_group": "all|adm\nGET status"}},
            id="line break in a contact group",
        ),
        pytest.param({"serviceregex": {"service_regex": "CPU["}}, id="invalid regex"),
        pytest.param({"output": {"service_output": "(timeout"}}, id="invalid summary regex"),
    ],
)
def test_a_dashboard_filter_the_table_cannot_apply_is_reported(context: VisualContext) -> None:
    translation = translate_filters(context)

    assert (translation.filter, translation.unapplied) == (None, list(context))
