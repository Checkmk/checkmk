#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: Checkmk Enterprise License
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from http import HTTPStatus

from cmk.agent_receiver.config import Config
from cmk.relay_protocols.relays import RelayRegistrationResponse
from cmk.relay_protocols.tasks import FetchAdHocTask
from cmk.testlib.agent_receiver.agent_receiver import AgentReceiverClient
from cmk.testlib.agent_receiver.config_file_system import create_config_folder
from cmk.testlib.agent_receiver.site_mock import OP, SiteMock


def test_create_task_unknow_relay(
    agent_receiver: AgentReceiverClient,
    site: SiteMock,
    site_context: Config,
) -> None:
    site.set_scenario([], [("relay1", OP.ADD)])
    relay_id = register_relay(agent_receiver, "relay1")
    cf = create_config_folder(root=site_context.omd_root, relays=[relay_id])
    agent_receiver.set_serial(cf.serial)

    response = agent_receiver.push_task(relay_id="bad_relay_id", spec=FetchAdHocTask(payload=".."))
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert "bad_relay_id" in response.json()["detail"]


# TODO duplicate code
def register_relay(ar: AgentReceiverClient, name: str) -> str:
    resp = ar.register_relay(name)
    parsed = RelayRegistrationResponse.model_validate_json(resp.text)
    return parsed.relay_id
