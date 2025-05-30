#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from unittest.mock import call

import pytest
from pytest_mock import MockerFixture

from tests.testlib.unit.rest_api_client import ClientRegistry

from cmk.gui.watolib.automations import LocalAutomationConfig


@pytest.mark.usefixtures("inline_background_jobs")
def test_openapi_parent_scan_background(
    clients: ClientRegistry,
    mocker: MockerFixture,
) -> None:
    clients.HostConfig.bulk_create(
        entries=[
            {
                "host_name": "foobar",
                "folder": "/",
            },
            {
                "host_name": "sample",
                "folder": "/",
            },
        ]
    )

    automation = mocker.patch("cmk.gui.watolib.parent_scan.scan_parents")
    resp = clients.ParentScan.start(
        host_names=["foobar", "sample"],
        gateway_hosts={
            "option": "create_in_folder",
            "folder": "/",
            "hosts_alias": "Created by parent scan",
        },
    )

    automation.assert_has_calls(
        [
            call(
                automation_config=LocalAutomationConfig(),
                host_name="foobar",
                timeout=8,
                probes=2,
                max_ttl=10,
                ping_probes=5,
                debug=False,
            ),
            call().results.__iter__(),
            call(
                automation_config=LocalAutomationConfig(),
                host_name="sample",
                timeout=8,
                probes=2,
                max_ttl=10,
                ping_probes=5,
                debug=False,
            ),
            call().results.__iter__(),
        ]
    )
    assert resp.json["id"] == "parent_scan"
    assert resp.json["title"].endswith("is active") or resp.json["title"].endswith("is finished"), (
        resp.json
    )
    assert "active" in resp.json["extensions"]
    assert "state" in resp.json["extensions"]
    assert "result" in resp.json["extensions"]["logs"]
    assert "progress" in resp.json["extensions"]["logs"]
