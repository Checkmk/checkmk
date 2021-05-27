#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pytest

pytestmark = pytest.mark.checks

from cmk.base.plugins.agent_based.agent_based_api.v1 import State, Result, Service

from cmk.base.plugins.agent_based.fuse_system_alerts import (
    discovery_fuse_system_alerts,
    check_fuse_system_alerts
)


PARSED = [
    {
        "id": "45fa59b7-cf49-40fb-ab19-7de59f80da45", 
        "name": "system-1", 
        "type": "OTCS", 
        "component_type": "System Status", 
        "errors": 0, 
        "warnings": 0, 
        "link": ""
    },
    {
        "id": "78fea62b-1a14-4e82-8385-70817ccd6388", 
        "name": "system-2", 
        "type": "OTAC", 
        "component_type": "System Status", 
        "errors": 0, 
        "warnings": 0, 
        "link": ""
    },
    {
        "id": "78fea62b-1a14-4e82-8385-70817ccd6388", 
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
                parameters={"id":"45fa59b7-cf49-40fb-ab19-7de59f80da45", "component_type":"System Status"}
            ),
            Service(
                item="OTAC - system-2 - System Status",
                parameters={"id":"78fea62b-1a14-4e82-8385-70817ccd6388", "component_type":"System Status"}
            ),
            Service(
                item="OTAC - system-2 - Logical Archives",
                parameters={"id":"78fea62b-1a14-4e82-8385-70817ccd6388", "component_type":"Logical Archives"}
            )
        ]
    )
])
def test_discovery_fuse_system_alerts(params, result):
    service = discovery_fuse_system_alerts(params)
    assert next(service) == result[0]
    assert next(service) == result[1]
    assert next(service) == result[2]


@pytest.mark.parametrize('params,result', [
    (
        {
            "id":"45fa59b7-cf49-40fb-ab19-7de59f80da45",
            "component_type":"System Status"
        },
        Result(
            state=State.OK, 
            summary="Errors: 0 | Warnings: 0"
        )
    ),
    (
        {
            "id":"78fea62b-1a14-4e82-8385-70817ccd6388",
            "component_type":"System Status"
        },
        Result(
            state=State.OK, 
            summary="Errors: 0 | Warnings: 0"
        )
    ),
    (
        {
            "id":"78fea62b-1a14-4e82-8385-70817ccd6388",
            "component_type":"Logical Archives"
        },
        Result(
            state=State.WARN,
            summary="Errors: 0 | Warnings: 12 | <a href=\"link_system-2_OTAC_ARCHIVE\" target=\"_blank\">click here for more info</a>"
        )
    )
])
def test_check_fuse_system_alerts(params, result):
    assert next(check_fuse_system_alerts("", params, PARSED)) == result
