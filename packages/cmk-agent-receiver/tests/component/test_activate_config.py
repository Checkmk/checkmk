#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: Checkmk Enterprise License
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import uuid
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
    relay_id_a = str(uuid.uuid4())
    relay_id_b = str(uuid.uuid4())
    site.set_scenario([relay_id_a, relay_id_b])

    serial_folder = create_config_folder(site_context.omd_root, [relay_id_a, relay_id_b])

    # Simulate user activation. Call to the endpoint that creates a ActivateConfigTask for each relay
    resp = agent_receiver.activate_config()
    assert resp.status_code == HTTPStatus.OK, resp.text

    # Assert each relay has exactly one pending config task with correct serial
    _assert_single_pending_config_task(agent_receiver, relay_id_a, serial_folder.serial)
    _assert_single_pending_config_task(agent_receiver, relay_id_b, serial_folder.serial)


def test_activation_performed_twice_with_same_config(
    site: SiteMock,
    agent_receiver: AgentReceiverClient,
    site_context: Config,
) -> None:
    # Start AR with two relays configured in the site
    relay_id_a = str(uuid.uuid4())
    relay_id_b = str(uuid.uuid4())
    site.set_scenario([relay_id_a, relay_id_b])

    serial_folder = create_config_folder(site_context.omd_root, [relay_id_a, relay_id_b])

    # Simulate user activation. Call to the endpoint that creates a ActivateConfigTask for each relay
    resp = agent_receiver.activate_config()
    assert resp.status_code == HTTPStatus.OK, resp.text

    # Assert each relay has exactly one pending config task with correct serial
    _assert_single_pending_config_task(agent_receiver, relay_id_a, serial_folder.serial)
    _assert_single_pending_config_task(agent_receiver, relay_id_b, serial_folder.serial)

    # Simulate second user activation.
    resp = agent_receiver.activate_config()
    assert resp.status_code == HTTPStatus.OK, resp.text

    # Assert each relay has exactly one pending config task with correct serial
    _assert_single_pending_config_task(agent_receiver, relay_id_a, serial_folder.serial)
    _assert_single_pending_config_task(agent_receiver, relay_id_b, serial_folder.serial)


def _assert_single_pending_config_task(
    agent_receiver: AgentReceiverClient,
    relay_id: str,
    expected_serial: str,
) -> None:
    tasks = get_relay_tasks(agent_receiver, relay_id)
    assert len(tasks.tasks) == 1, tasks
    task = tasks.tasks[0]
    assert isinstance(task.spec, RelayConfigTask)
    assert task.spec.tar_data == ""
    assert task.spec.serial == expected_serial
    assert task.status == TaskStatus.PENDING
