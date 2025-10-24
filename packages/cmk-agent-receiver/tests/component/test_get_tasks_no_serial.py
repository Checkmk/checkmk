#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import uuid

from cmk.agent_receiver.config import Config
from cmk.testlib.agent_receiver.agent_receiver import AgentReceiverClient
from cmk.testlib.agent_receiver.config_file_system import create_config_folder
from cmk.testlib.agent_receiver.site_mock import SiteMock
from cmk.testlib.agent_receiver.tasks import get_relay_tasks


def test_get_tasks_works_if_no_serial_is_given(
    site: SiteMock,
    site_context: Config,
    agent_receiver: AgentReceiverClient,
) -> None:
    # register two relays
    relay_id_1 = str(uuid.uuid4())
    site.set_scenario([relay_id_1])
    _ = create_config_folder(root=site_context.omd_root, relays=[relay_id_1])

    # asking with an incorrect serial
    relay_1_tasks = get_relay_tasks(agent_receiver, relay_id_1, status="PENDING").tasks

    assert len(relay_1_tasks) == 0
