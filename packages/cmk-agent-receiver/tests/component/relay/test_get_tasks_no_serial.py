#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import uuid
from http import HTTPStatus

from fastapi.testclient import TestClient

from cmk.relay_protocols.tasks import TaskListResponse
from cmk.testlib.agent_receiver.clients import RelayClient
from cmk.testlib.agent_receiver.site_mock import SiteMock


def test_get_tasks_works_if_no_serial_is_given(
    site: SiteMock,
    test_client: TestClient,
) -> None:
    """Verify that requesting tasks without providing a serial succeeds and returns an empty task list.

    Test steps:
    1. Configure relay without setting serial
    2. Request tasks for the relay
    3. Verify request succeeds with empty task list
    """
    relay_id_1 = str(uuid.uuid4())
    site.set_scenario([relay_id_1])
    site.push_config([relay_id_1])

    # Create relay client without calling apply_config() - this means no Serial header is sent
    relay = RelayClient(test_client, site.site_name, relay_id_1)
    response = relay.get_tasks(status="PENDING")
    assert response.status_code == HTTPStatus.OK, response.text
    relay_1_tasks = TaskListResponse.model_validate(response.json()).tasks

    assert len(relay_1_tasks) == 0
