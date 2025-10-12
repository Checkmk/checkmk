#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import uuid

from cmk.agent_receiver.config import Config
from cmk.relay_protocols.tasks import RelayConfigTask
from cmk.testlib.agent_receiver.agent_receiver import AgentReceiverClient
from cmk.testlib.agent_receiver.config_file_system import create_config_folder
from cmk.testlib.agent_receiver.site_mock import SiteMock
from cmk.testlib.agent_receiver.tasks import get_relay_tasks


def test_config_update_triggered_by_outdated_serial(
    site: SiteMock,
    site_context: Config,
    agent_receiver: AgentReceiverClient,
) -> None:
    # register two relays
    relay_id_1 = str(uuid.uuid4())
    relay_id_2 = str(uuid.uuid4())
    site.set_scenario([relay_id_1, relay_id_2])
    cf = create_config_folder(root=site_context.omd_root, relays=[relay_id_1, relay_id_2])

    # asking with an incorrect serial
    old_serial = "some-old-serial"
    agent_receiver.set_serial(old_serial)
    relay_1_tasks = get_relay_tasks(agent_receiver, relay_id_1, status="PENDING").tasks

    assert len(relay_1_tasks) == 1
    task = relay_1_tasks[0]
    assert isinstance(task.spec, RelayConfigTask)
    assert task.spec.serial == cf.serial
    cf.assert_tar_content(relay_id_1, task.spec.tar_data)

    # asking with correct serial, no task created in this case
    agent_receiver.set_serial(cf.serial)
    relay_2_tasks = get_relay_tasks(agent_receiver, relay_id_2, status="PENDING").tasks
    assert len(relay_2_tasks) == 0


def test_config_update_triggered_by_outdated_serial_is_generated_once(
    site: SiteMock,
    site_context: Config,
    agent_receiver: AgentReceiverClient,
) -> None:
    # register two relays
    relay_id_1 = str(uuid.uuid4())
    site.set_scenario([relay_id_1])
    cf = create_config_folder(root=site_context.omd_root, relays=[relay_id_1])

    # asking with an incorrect serial
    old_serial = "some-old-serial"
    agent_receiver.set_serial(old_serial)
    relay_1_tasks = get_relay_tasks(agent_receiver, relay_id_1, status="PENDING").tasks

    assert len(relay_1_tasks) == 1
    task = relay_1_tasks[0]
    assert isinstance(task.spec, RelayConfigTask)
    assert task.spec.serial == cf.serial
    cf.assert_tar_content(relay_id_1, task.spec.tar_data)

    tasklist = get_relay_tasks(agent_receiver, relay_id_1, status="PENDING").tasks
    assert len(tasklist) == 1
    assert tasklist[0].id == task.id
