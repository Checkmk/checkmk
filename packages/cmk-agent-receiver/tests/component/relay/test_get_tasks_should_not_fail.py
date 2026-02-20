#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_receiver.lib.config import Config
from cmk.agent_receiver.relay.lib.shared_types import Serial
from cmk.testlib.agent_receiver.agent_receiver import AgentReceiverClient
from cmk.testlib.agent_receiver.config_file_system import create_config_folder
from cmk.testlib.agent_receiver.site_mock import SiteMock
from cmk.testlib.agent_receiver.tasks import get_relay_tasks


def test_relay_without_folder(
    agent_receiver: AgentReceiverClient,
    site_context: Config,
    site: SiteMock,
) -> None:
    """Verify that retrieving tasks for a relay without a corresponding filesystem folder succeeds without errors.

    Test steps:
    1. Register relay without corresponding folder in filesystem
    2. Request tasks for the relay
    3. Verify request succeeds with no tasks created
    """

    stale_serial = Serial.default()
    cf = create_config_folder(root=site_context.omd_root, relays=["relay_id_1", "relay_id_3"])
    assert cf.serial != stale_serial
    agent_receiver.set_serial(stale_serial)
    site.set_scenario(["relay_1", "relay_2", "relay_3"])

    response = get_relay_tasks(agent_receiver=agent_receiver, relay_id="relay_2")
    assert len(response.tasks) == 0
