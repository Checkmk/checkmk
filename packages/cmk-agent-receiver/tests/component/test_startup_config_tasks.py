#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

from http import HTTPStatus

from fastapi.testclient import TestClient

from cmk.agent_receiver.config import Config
from cmk.agent_receiver.main import main_app
from cmk.relay_protocols.tasks import RelayConfigTask, TaskStatus
from cmk.testlib.agent_receiver.agent_receiver import AgentReceiverClient
from cmk.testlib.agent_receiver.config_file_system import create_config_folder
from cmk.testlib.agent_receiver.site_mock import SiteMock
from cmk.testlib.agent_receiver.tasks import get_relay_tasks


def test_startup_creates_config_tasks_for_existing_relays(
    site: SiteMock,
    site_context: Config,
) -> None:
    relay_id_a = "relay_start_a"
    relay_id_b = "relay_start_b"
    site.set_scenario([relay_id_a, relay_id_b])

    serial_folder = create_config_folder(site_context.omd_root, [relay_id_a, relay_id_b])

    app = main_app()
    with TestClient(app) as client:
        agent = AgentReceiverClient(client, site_context.site_name, site.user, serial_folder.serial)

        tasks_a = get_relay_tasks(agent, relay_id_a)
        assert len(tasks_a.tasks) == 1
        task_a = tasks_a.tasks[0]
        assert isinstance(task_a.spec, RelayConfigTask)
        assert task_a.spec.serial == serial_folder.serial
        assert task_a.status == TaskStatus.PENDING

        tasks_b = get_relay_tasks(agent, relay_id_b)
        assert len(tasks_b.tasks) == 1
        task_b = tasks_b.tasks[0]
        assert isinstance(task_b.spec, RelayConfigTask)
        assert task_b.spec.serial == serial_folder.serial
        assert task_b.status == TaskStatus.PENDING

        # Health check service is already available
        health = client.get(f"/{site_context.site_name}/agent-receiver/openapi.json")
        assert health.status_code == HTTPStatus.OK, health.text
