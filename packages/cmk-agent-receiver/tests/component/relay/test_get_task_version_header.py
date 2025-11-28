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
from cmk.testlib.agent_receiver.tasks import add_tasks


def test_get_task_returns_version_header(
    site: SiteMock,
    site_context: Config,
    agent_receiver: AgentReceiverClient,
) -> None:
    # register a relay and create a task
    relay_id = str(uuid.uuid4())
    site.set_scenario([relay_id])
    _ = create_config_folder(root=site_context.omd_root, relays=[relay_id])

    # create a task
    task_ids = add_tasks(count=1, agent_receiver=agent_receiver, relay_id=relay_id)
    task_id = task_ids[0]

    # get the specific task
    response = agent_receiver.client.get(
        f"/{agent_receiver.site_name}/relays/{relay_id}/tasks/{task_id}"
    )

    assert response.status_code == HTTPStatus.OK
    assert HEADERS.VERSION in response.headers
    # Note: site_context is using "some.detailed.version.ultimate" as version in the test setup
    assert response.headers[HEADERS.VERSION] == "some.detailed.version"
