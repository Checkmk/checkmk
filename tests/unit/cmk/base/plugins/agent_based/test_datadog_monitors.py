#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State
from cmk.base.plugins.agent_based.datadog_monitors import (
    _DEFAULT_DATADOG_AND_CHECKMK_STATES,
    check_datadog_monitors,
    discover_datadog_monitors,
    Monitor,
    parse_datadog_monitors,
)

from cmk.gui.plugins.wato.check_parameters.datadog_monitors import (
    _DEFAULT_DATADOG_AND_CHECKMK_STATES as WATO_DEFAULTS,
)

_SECTION = {
    "[Auto] Clock in sync with NTP": Monitor(
        state="OK",
        message="Triggers if any host's clock goes out of sync with the time given by NTP. The offset threshold is configured in the Agent's `ntp.yaml` file.\n\nPlease read the [KB article](https://docs.datadoghq.com/agent/faq/network-time-protocol-ntp-offset-issues) on NTP Offset issues for more details on cause and resolution.",
        thresholds={"warning": 1, "ok": 1, "critical": 1},
        tags=[],
    ),
    "[SLO] Article Delta Update Device Delay": Monitor(
        state="Alert",
        message="Devices in env {{env.name}} receive article updates delayed!",
        thresholds={"critical": 180.0},
        tags=["slo", "nemo"],
    ),
    "staging | IDM Gateway Service | Import Error Rate": Monitor(
        state="OK",
        message="IDM Gateway Service has a high error count @slack-nemo-alerts",
        thresholds={},
        tags=["checkmk", "env:staging", "process:login", "service:idm-gateway-service"],
    ),
}


def test_parse_datadog_monitors():
    assert (
        parse_datadog_monitors(
            [
                [
                    '{"restricted_roles": null, "tags": [], "deleted": null, "query": "\\"ntp.in_sync\\".over(\\"*\\").last(2).count_by_status()", "message": "Triggers if any host\'s clock goes out of sync with the time given by NTP. The offset threshold is configured in the Agent\'s `ntp.yaml` file.\\n\\nPlease read the [KB article](https://docs.datadoghq.com/agent/faq/network-time-protocol-ntp-offset-issues) on NTP Offset issues for more details on cause and resolution.", "matching_downtimes": [], "id": 163839, "multi": true, "name": "[Auto] Clock in sync with NTP", "created": "2020-05-27T23:16:40.352171+00:00", "created_at": 1590621400000, "creator": {"id": 1000074841, "handle": "support-edekadigitalnmww", "name": "Datadog Support", "email": "support-user-prod@datadoghq.com"}, "org_id": 1000017658, "modified": "2020-05-27T23:16:40.352171+00:00", "priority": null, "overall_state_modified": "2020-06-04T12:58:40+00:00", "overall_state": "OK", "type": "service check", "options": {"thresholds": {"warning": 1, "ok": 1, "critical": 1}, "silenced": {}}}'
                ],
                [
                    '{"restricted_roles": null, "tags": ["slo", "nemo"], "deleted": null, "query": "min(last_1m):p95:nemo.process_time{entity_type:article_update} by {env} > 180", "message": "Devices in env {{env.name}} receive article updates delayed!", "matching_downtimes": [], "id": 423891, "multi": true, "name": "[SLO] Article Delta Update Device Delay", "created": "2020-11-18T09:13:17.593708+00:00", "created_at": 1605690797000, "creator": {"id": 1000108584, "handle": "finn.poppinga@freiheit.com", "name": "Finn Poppinga", "email": "finn.poppinga@freiheit.com"}, "org_id": 1000017658, "modified": "2020-11-18T09:13:17.593708+00:00", "priority": null, "overall_state_modified": "2021-03-18T08:15:53+00:00", "overall_state": "Alert", "type": "metric alert", "options": {"notify_audit": false, "locked": false, "timeout_h": 0, "silenced": {}, "include_tags": true, "no_data_timeframe": null, "require_full_window": true, "new_host_delay": 300, "notify_no_data": false, "renotify_interval": 0, "escalation_message": "", "thresholds": {"critical": 180.0}}}'
                ],
                [
                    '{"restricted_roles": null, "tags": ["checkmk", "env:staging", "process:login", "service:idm-gateway-service"], "deleted": null, "query": "sum(last_10m):default_zero(sum:nemo.process_count{env:staging,service:idm-gateway-service,status:error}.as_count())/(sum:nemo.process_count{env:staging,service:idm-gateway-service}.as_count()) > 0", "message": "IDM Gateway Service has a high error count @slack-nemo-alerts", "matching_downtimes": [], "id": 718433, "multi": false, "name": "staging | IDM Gateway Service | Import Error Rate", "created": "2021-02-19T23:31:44.059653+00:00", "created_at": 1613777504000, "creator": {"id": 1000075168, "handle": "hassan.youssef@freiheit.com", "name": "Hassan Youssef", "email": "hassan.youssef@freiheit.com"}, "org_id": 1000017658, "modified": "2021-02-23T13:54:16.861819+00:00", "priority": null, "overall_state_modified": "2021-03-14T19:19:04+00:00", "overall_state": "OK", "type": "query alert", "options": {"notify_audit": false, "locked": false, "silenced": {}, "include_tags": true, "no_data_timeframe": 2880, "new_host_delay": 300, "require_full_window": true, "notify_no_data": true, "thresholds": {}}}',
                ],
            ]
        )
        == _SECTION
    )


@pytest.mark.parametrize(
    "params, expected_result",
    (
        pytest.param(
            {
                "states_discover": [
                    "Alert",
                    "Ignored",
                    "No Data",
                    "OK",
                    "Skipped",
                    "Unknown",
                    "Warn",
                ],
            },
            [
                Service(item="[Auto] Clock in sync with NTP"),
                Service(item="[SLO] Article Delta Update Device Delay"),
                Service(item="staging | IDM Gateway Service | Import Error Rate"),
            ],
            id="no custom discovery params",
        ),
        pytest.param(
            {
                "states_discover": [],
            },
            [],
            id="custom discovery params",
        ),
    ),
)
def test_discover_datadog_monitors(params, expected_result):
    assert (
        list(
            discover_datadog_monitors(
                params,
                _SECTION,
            )
        )
        == expected_result
    )


@pytest.mark.parametrize(
    "item, params, expected_result",
    (
        pytest.param(
            "[SLO] Article Delta Update Device Delay",
            {
                "state_mapping": {
                    "Alert": State.CRIT,
                    "Ignored": State.UNKNOWN,
                    "No Data": State.UNKNOWN,
                    "OK": State.OK,
                    "Skipped": State.UNKNOWN,
                    "Unknown": State.UNKNOWN,
                    "Warn": State.WARN,
                },
                "tags_to_show": [],
            },
            [
                Result(
                    state=State.CRIT,
                    summary="Overall state: Alert",
                    details="Devices in env {{env.name}} receive article updates delayed!",
                ),
                Result(
                    state=State.OK,
                    summary="Datadog thresholds: critical: 180.0",
                ),
            ],
            id="standard case",
        ),
        pytest.param(
            "staging | IDM Gateway Service | Import Error Rate",
            {
                "state_mapping": {
                    "Alert": State.CRIT,
                    "Ignored": State.UNKNOWN,
                    "No Data": State.UNKNOWN,
                    "OK": State.OK,
                    "Skipped": State.UNKNOWN,
                    "Unknown": State.UNKNOWN,
                    "Warn": State.WARN,
                },
                "tags_to_show": [],
            },
            [
                Result(
                    state=State.OK,
                    summary="Overall state: OK",
                    details="IDM Gateway Service has a high error count @slack-nemo-alerts",
                ),
            ],
            id="no thresholds",
        ),
        pytest.param(
            "[SLO] Article Delta Update Device Delay",
            {
                "state_mapping": {
                    "Alert": 0,
                    "Ignored": 0,
                    "No Data": 0,
                    "OK": 1,
                    "Skipped": 0,
                    "Unknown": 0,
                    "Warn": 0,
                },
                "tags_to_show": [
                    "slo",
                    ".*nemo.*",
                ],
            },
            [
                Result(
                    state=State.OK,
                    summary="Overall state: Alert",
                    details="Devices in env {{env.name}} receive article updates delayed!",
                ),
                Result(
                    state=State.OK,
                    summary="Datadog thresholds: critical: 180.0",
                ),
                Result(
                    state=State.OK,
                    summary="Datadog tags: slo, nemo",
                ),
            ],
            id="with tags and custom states",
        ),
    ),
)
def test_check_datadog_monitors(item, params, expected_result):
    assert (
        list(
            check_datadog_monitors(
                item,
                params,
                _SECTION,
            )
        )
        == expected_result
    )


def test_default_datadog_and_checkmk_states():
    assert _DEFAULT_DATADOG_AND_CHECKMK_STATES == WATO_DEFAULTS
