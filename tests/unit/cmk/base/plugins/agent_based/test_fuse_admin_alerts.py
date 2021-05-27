#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pytest

pytestmark = pytest.mark.checks

from cmk.base.plugins.agent_based.agent_based_api.v1 import State, Result, Service

from cmk.base.plugins.agent_based.fuse_admin_alerts import (
    discovery_fuse_admin_alerts,
    check_fuse_admin_alerts
)


PARSED = [
    {
        "id": "", 
        "name": "", 
        "type": "", 
        "component_type": "Health", 
        "errors": 0, 
        "warnings": 7, 
        "link": "link_FUSE_HEALTH"
    }
]


@pytest.mark.parametrize('params,result', [
    (
        PARSED,
        Service(item="Health")
    )
])
def test_discovery_fuse_admin_alerts(params, result):
    service = discovery_fuse_admin_alerts(params)
    assert next(service) == result


@pytest.mark.parametrize('params,result', [
    (
        "Health",
        Result(
            state=State.WARN, 
            summary="Errors: 0 | Warnings: 7 | <a href=\"link_FUSE_HEALTH\" target=\"_blank\">click here for more info</a>"
        )
    )
])
def test_check_fuse_admin_alerts(params, result):
    assert next(check_fuse_admin_alerts(params, PARSED)) == result
