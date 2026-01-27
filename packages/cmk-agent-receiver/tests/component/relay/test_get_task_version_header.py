#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import uuid
from http import HTTPStatus

from cmk.agent_receiver.lib.config import Config
from cmk.relay_protocols.tasks import HEADERS
from cmk.testlib.agent_receiver.agent_receiver import AgentReceiverClient
from cmk.testlib.agent_receiver.config_file_system import create_config_folder
from cmk.testlib.agent_receiver.site_mock import SiteMock


def test_get_tasks_returns_version_header(
    site: SiteMock,
    site_context: Config,
    agent_receiver: AgentReceiverClient,
) -> None:
    """Verify that the get tasks endpoint includes the version header in the response.

    Test steps:
    1. Register relay and create a task
    2. Retrieve specific task via endpoint
    3. Verify response includes version header
    """
    # register a relay and create a task
    relay_id = str(uuid.uuid4())
    site.set_scenario([relay_id])
    _ = create_config_folder(root=site_context.omd_root, relays=[relay_id])

    response = agent_receiver.get_relay_tasks(relay_id)

    assert response.status_code == HTTPStatus.OK, response.text
    assert HEADERS.VERSION in response.headers
    # Note: site_context is using "some.detailed.version.ultimate" as version in the test setup
    assert response.headers[HEADERS.VERSION] == "some.detailed.version"
