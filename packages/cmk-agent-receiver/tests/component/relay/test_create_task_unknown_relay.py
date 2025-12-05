#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: Checkmk Enterprise License
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from http import HTTPStatus

from cmk.agent_receiver.lib.config import Config
from cmk.relay_protocols.tasks import FetchAdHocTask
from cmk.testlib.agent_receiver.agent_receiver import AgentReceiverClient, register_relay
from cmk.testlib.agent_receiver.config_file_system import create_config_folder
from cmk.testlib.agent_receiver.relay import random_relay_id
from cmk.testlib.agent_receiver.site_mock import OP, SiteMock


def test_create_task_unknown_relay(
    agent_receiver: AgentReceiverClient,
    site: SiteMock,
    site_context: Config,
) -> None:
    # We allow creating tasks for unknown relays. For now it's the site's responsibility
    # to handle such cases.
    relay_id = random_relay_id()
    site.set_scenario([], [(relay_id, OP.ADD)])
    register_relay(agent_receiver, name="relay1", relay_id=relay_id)
    cf = create_config_folder(root=site_context.omd_root, relays=[relay_id])
    agent_receiver.set_serial(cf.serial)

    response = agent_receiver.push_task(relay_id="bad_relay_id", spec=FetchAdHocTask(payload=".."))
    assert response.status_code == HTTPStatus.OK
    assert response.json()["task_id"] is not None
