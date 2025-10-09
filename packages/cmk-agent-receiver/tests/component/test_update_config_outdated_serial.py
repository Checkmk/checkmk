#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import uuid

from cmk.agent_receiver.config import Config
from cmk.relay_protocols.tasks import RelayConfigTask, TaskStatus
from cmk.testlib.agent_receiver.agent_receiver import AgentReceiverClient
from cmk.testlib.agent_receiver.config_file_system import create_config_folder
from cmk.testlib.agent_receiver.site_mock import SiteMock
from cmk.testlib.agent_receiver.tasks import get_all_tasks


def test_config_update_triggered_by_outdated_serial(
    site: SiteMock,
    site_context: Config,
    agent_receiver: AgentReceiverClient,
) -> None:
    # register two relays

    old_serial = "some-old-serial"

    relay_id_1 = str(uuid.uuid4())
    relay_id_2 = str(uuid.uuid4())

    site.set_scenario([relay_id_1, relay_id_2])
    cf = create_config_folder(root=site_context.omd_root, relays=[relay_id_1, relay_id_2])

    # asking with an incorrect serial

    agent_receiver.set_serial(old_serial)
    relay_1_tasks = get_all_tasks(agent_receiver, relay_id_1)
    assert len(relay_1_tasks) == 1
    task = relay_1_tasks[0]
    assert task.status == TaskStatus.PENDING
    assert isinstance(task.spec, RelayConfigTask)
    assert task.spec.serial == cf.serial
    cf.assert_tar_content(relay_id_1, task.spec.tar_data)

    # asking with correct serial, no task created in this case

    agent_receiver.set_serial(cf.serial)
    relay_2_tasks = get_all_tasks(agent_receiver, relay_id_2)
    assert len(relay_2_tasks) == 0
