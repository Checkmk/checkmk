#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json

import pytest
from pytest_mock import MockerFixture

import cmk.utils.version as cmk_version

mocked_phase_one_result = {
    "class_name": "Phase1Result",
    "attributes": {
        "connector_object": "PiggybackHosts",
        "attributes": {
            "hosts": ["some_host"],
            "tmpfs_initialization_time": 100000,
        },
        "status": {
            "class_name": "ExecutionStatus",
            "attributes": {"_steps": []},
            "_finished": True,
            "_time_initialized": 100000,
            "_time_completed": 100001,
        },
    },
}


@pytest.mark.skipif(cmk_version.is_raw_edition(), reason="DCD not available in raw edition")
def test_dcd_fetch_phase_one_result(
    wsgi_app,
    with_automation_user,
    mocker: MockerFixture,
):
    automation_patch = mocker.patch(
        "cmk.gui.watolib.automations.execute_phase1_result",
        return_value=mocked_phase_one_result,
    )

    username, secret = with_automation_user
    wsgi_app.set_authorization(("Bearer", username + " " + secret))

    resp = wsgi_app.call_method(
        "post",
        "/NO_SITE/check_mk/api/1.0/domain-types/dcd/actions/fetch_phase_one/invoke",
        params=json.dumps(
            {
                "site_id": "NO_SITE",
                "connection_id": "connection_one",
            }
        ),
        headers={"Accept": "application/json"},
        content_type="application/json",
        status=200,
    )
    automation_patch.assert_called_once()
    assert resp.json["extensions"] == mocked_phase_one_result
