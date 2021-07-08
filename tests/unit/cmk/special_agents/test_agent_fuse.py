#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pytest

from cmk.special_agents.agent_fuse import (
    SummaryStructure,
    Alert,
    get_summary_structure,
    get_systems_alerts,
    get_environment_alerts,
    get_admin_alerts
)

pytestmark = pytest.mark.checks

LAYOUT: dict = {
    "systems": [
        {
            "id": "45fa59b7-cf49-40fb-ab19-7de59f80da57",
            "name": "system-1",
            "componentTypes": [
                {
                    "id": "SYSTEM",
                    "displayName": "System Status"
                }
            ],
            "type": "OTCS"
        },
        {
            "id": "78fea62b-1a14-4e82-8385-70817ccd6312",
            "name": "system-2",
            "componentTypes": [
                {
                    "id": "SYSTEM",
                    "displayName": "System Status"
                },
                {
                    "id": "OTAC_ARCHIVE",
                    "displayName": "Logical Archives"
                }
            ],
            "type": "OTAC"
        }
    ],
    "environments": [
        {
            "id": "378ae807-48f8-44b4-9da4-159413b17157",
            "name": "PRODUCTION",
            "componentTypes": [
                {
                    "id": "SOV",
                    "displayName": "System Object Volume"
                },
                {
                    "id": "AGENTS",
                    "displayName": "Agents"
                }
            ]
        }
    ],
    "admin": {
        "componentTypes": [
            {
                "id": "HEALTH",
                "displayName": "Health"
            }
        ]
    }
}


SUMMARY: list = [
    {
        "componentType": "OTAC_ARCHIVE",
        "envId": "378ae807-48f8-44b4-9da4-159413b17157",
        "systemId": "78fea62b-1a14-4e82-8385-70817ccd6312",
        "warnings": 12.0,
        "link": "link_system-2_OTAC_ARCHIVE"
    },
    {
        "componentType": "SOV",
        "envId": "378ae807-48f8-44b4-9da4-159413b17157",
        "warnings": 2.0,
        "errors": 10.0,
        "link": "link_PRODUCTION_SOV"
    },
    {
        "componentType": "HEALTH",
        "warnings": 7.0,
        "link": "link_FUSE_HEALTH"
    }
]


SUMMARY_STRUCTURE: SummaryStructure = SummaryStructure(
    {("78fea62b-1a14-4e82-8385-70817ccd6312", "OTAC_ARCHIVE"):
        {
            "componentType": "OTAC_ARCHIVE",
            "envId": "378ae807-48f8-44b4-9da4-159413b17157",
            "systemId": "78fea62b-1a14-4e82-8385-70817ccd6312",
            "warnings": 12.0,
            "link": "link_system-2_OTAC_ARCHIVE"
        }
    },
    {("378ae807-48f8-44b4-9da4-159413b17157", "SOV"):
        {
            "componentType": "SOV",
            "envId": "378ae807-48f8-44b4-9da4-159413b17157",
            "warnings": 2.0,
            "errors": 10.0,
            "link": "link_PRODUCTION_SOV"
        }
    },
    {"HEALTH":
        {
            "componentType": "HEALTH",
            "warnings": 7.0,
            "link": "link_FUSE_HEALTH"
        }
    }
)

@pytest.mark.parametrize('params,result', [
    (
        SUMMARY,
        SUMMARY_STRUCTURE
    )
])
def test_get_summary_structure(params, result):
    assert get_summary_structure(params) == result


@pytest.mark.parametrize('params,result', [
    (
        {
            "layout": LAYOUT,
            "system_alerts": SUMMARY_STRUCTURE.system_alerts
        },
        [
            Alert(
                "45fa59b7-cf49-40fb-ab19-7de59f80da57",
                "system-1",
                "OTCS",
                "System Status",
                0,
                0,
                ""
            ),
            Alert(
                "78fea62b-1a14-4e82-8385-70817ccd6312",
                "system-2",
                "OTAC",
                "System Status",
                0,
                0,
                ""
            ),
            Alert(
                "78fea62b-1a14-4e82-8385-70817ccd6312",
                "system-2",
                "OTAC",
                "Logical Archives",
                0,
                12,
                "link_system-2_OTAC_ARCHIVE"
            )
        ]
    )
])
def test_get_systems_alerts(params, result):
    assert get_systems_alerts(params["layout"], params["system_alerts"]) == result


@pytest.mark.parametrize('params,result', [
    (
        {
            "layout": LAYOUT,
            "env_alerts": SUMMARY_STRUCTURE.env_alerts
        },
        [
            Alert(
                "378ae807-48f8-44b4-9da4-159413b17157",
                "PRODUCTION",
                "",
                "System Object Volume",
                10,
                2,
                "link_PRODUCTION_SOV"
            ),
            Alert(
                "378ae807-48f8-44b4-9da4-159413b17157",
                "PRODUCTION",
                "",
                "Agents",
                0,
                0,
                ""
            )
        ]
    )
])
def test_get_environment_alerts(params, result):
    assert get_environment_alerts(params["layout"], params["env_alerts"]) == result


@pytest.mark.parametrize('params,result', [
    (
        {
            "layout": LAYOUT,
            "fuse_alerts": SUMMARY_STRUCTURE.fuse_alerts
        },
        [
            Alert("", "", "", "Health", 0, 7, "link_FUSE_HEALTH")
        ]
    )
])
def test_get_admin_alerts(params, result):
    assert get_admin_alerts(params["layout"], params["fuse_alerts"]) == result
