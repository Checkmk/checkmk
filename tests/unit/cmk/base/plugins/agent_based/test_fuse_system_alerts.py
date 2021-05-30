#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import State, Result, Service

from cmk.base.plugins.agent_based.fuse_system_alerts import (
    discovery_fuse_system_alerts,
    check_fuse_system_alerts
)

pytestmark = pytest.mark.checks

PARSED = [
    {
        "fuse_id": "45fa59b7-cf49-40fb-ab19-7de59f80da45",
        "name": "system-1",
        "type": "OTCS",
        "component_type": "System Status",
        "errors": 0,
        "warnings": 0,
        "link": ""
    },
    {
        "fuse_id": "78fea62b-1a14-4e82-8385-70817ccd6388",
        "name": "system-2",
        "type": "OTAC",
        "component_type": "System Status",
        "errors": 0,
        "warnings": 0,
        "link": ""
    },
    {
        "fuse_id": "78fea62b-1a14-4e82-8385-70817ccd6388",
        "name": "system-2",
        "type": "OTAC",
        "component_type": "Logical Archives",
        "errors": 0,
        "warnings": 12,
        "link": "link_system-2_OTAC_ARCHIVE"
    }
]


@pytest.mark.parametrize('params,result', [
    (
        PARSED,
        [
            Service(
                item="OTCS - system-1 - System Status",
                parameters={
                    "fuse_id":"45fa59b7-cf49-40fb-ab19-7de59f80da45",
                    "component_type":"System Status"
                }
            ),
            Service(
                item="OTAC - system-2 - System Status",
                parameters={
                    "fuse_id":"78fea62b-1a14-4e82-8385-70817ccd6388",
                    "component_type":"System Status"
                }
            ),
            Service(
                item="OTAC - system-2 - Logical Archives",
                parameters={
                    "fuse_id":"78fea62b-1a14-4e82-8385-70817ccd6388",
                    "component_type":"Logical Archives"
                }
            )
        ]
    )
])
def test_discovery_fuse_system_alerts(params, result):
    service = discovery_fuse_system_alerts(params)
    assert list(service) == result


@pytest.mark.parametrize('params,result', [
    (
        {
            "fuse_id":"45fa59b7-cf49-40fb-ab19-7de59f80da45",
            "component_type":"System Status"
        },
        [
            Result(
                state=State.OK,
                summary="Errors: 0 | Warnings: 0"
            )
        ]
    ),
    (
        {
            "fuse_id":"78fea62b-1a14-4e82-8385-70817ccd6388",
            "component_type":"System Status"
        },
        [
            Result(
                state=State.OK,
                summary="Errors: 0 | Warnings: 0"
            )
        ]
    ),
    (
        {
            "fuse_id":"78fea62b-1a14-4e82-8385-70817ccd6388",
            "component_type":"Logical Archives"
        },
        [
            Result(
                state=State.WARN,
                summary="Errors: 0 | Warnings: 12 | <a href=\"link_system-2_OTAC_ARCHIVE\" target=\"_blank\">click here for more info</a>"
            )
        ]
    )
])
def test_check_fuse_system_alerts(params, result):
    assert list(check_fuse_system_alerts("", params, PARSED)) == result
