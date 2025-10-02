#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: Checkmk Enterprise License
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from http import HTTPStatus

from cmk.agent_receiver.config import Config
from cmk.relay_protocols.tasks import RelayConfigTask, TaskStatus
from cmk.testlib.agent_receiver.agent_receiver import AgentReceiverClient
from cmk.testlib.agent_receiver.config_file_system import create_config_folder
from cmk.testlib.agent_receiver.site_mock import SiteMock
from cmk.testlib.agent_receiver.tasks import get_relay_tasks


def test_activation_performed_by_user_creates_config_tasks_for_each_relay(
    site: SiteMock,
    agent_receiver: AgentReceiverClient,
    site_context: Config,
) -> None:
    # Start AR with two relays configured in the site
    relay_id_a = "relay_id_a"
    relay_id_b = "relay_id_b"
    site.set_scenario([relay_id_a, relay_id_b])

    serial_folder = create_config_folder(site_context.omd_root, [relay_id_a, relay_id_b])

    # Simulate user activation. Call to the endpoint that creates a ActivateConfigTask for each relay
    resp = agent_receiver.activate_config()
    assert resp.status_code == HTTPStatus.OK, resp.text

    # Assert each relay has exactly one pending config task with correct serial
    tasks_a = get_relay_tasks(agent_receiver, relay_id_a)
    assert len(tasks_a.tasks) == 1, tasks_a
    task_a = tasks_a.tasks[0]
    assert isinstance(task_a.spec, RelayConfigTask)
    assert task_a.spec.tar_data == ""
    assert task_a.spec.serial == serial_folder.serial
    assert task_a.status == TaskStatus.PENDING

    tasks_b = get_relay_tasks(agent_receiver, relay_id_b)
    assert len(tasks_b.tasks) == 1, tasks_b
    task_b = tasks_b.tasks[0]
    assert isinstance(task_b.spec, RelayConfigTask)
    assert task_b.spec.tar_data == ""
    assert task_b.spec.serial == serial_folder.serial
    assert task_b.status == TaskStatus.PENDING
