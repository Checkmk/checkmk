#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from http import HTTPStatus

from fastapi.testclient import TestClient

from cmk.agent_receiver.relay.lib.shared_types import Serial
from cmk.relay_protocols.tasks import TaskListResponse
from cmk.testlib.agent_receiver.clients import RelayClient
from cmk.testlib.agent_receiver.relay_config_generator import RelayConfig
from cmk.testlib.agent_receiver.site_mock import SiteMock


def test_relay_without_folder(
    test_client: TestClient,
    site: SiteMock,
) -> None:
    """Verify that retrieving tasks for a relay without a corresponding filesystem folder succeeds without errors.

    Test steps:
    1. Register relay without corresponding folder in filesystem
    2. Request tasks for the relay
    3. Verify request succeeds with no tasks created
    """

    stale_serial = Serial.default()
    relay_config = site.push_config(["relay_id_1", "relay_id_3"])
    assert relay_config.serial != stale_serial
    site.set_scenario(["relay_1", "relay_2", "relay_3"])

    # Create relay client with the stale serial
    relay = RelayClient(test_client, site.site_name, "relay_2")
    relay.apply_config(RelayConfig(serial=stale_serial, files={}))
    response = relay.get_tasks()
    assert response.status_code == HTTPStatus.OK, response.text
    tasks = TaskListResponse.model_validate(response.json()).tasks
    assert len(tasks) == 0
