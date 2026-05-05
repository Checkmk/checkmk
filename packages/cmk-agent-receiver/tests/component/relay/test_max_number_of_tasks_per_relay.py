#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pathlib
import uuid
from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient

from cmk.agent_receiver.lib.config import get_config
from cmk.agent_receiver.main import main_app
from cmk.agent_receiver.relay.api.routers.relays.dependencies import (
    get_forward_monitoring_data_handler,
)
from cmk.agent_receiver.relay.api.routers.relays.handlers import ForwardMonitoringDataHandler
from cmk.relay_protocols.tasks import FetchAdHocTask
from cmk.testlib.agent_receiver.agent_receiver import AgentReceiverClient
from cmk.testlib.agent_receiver.builder import AgentReceiverConfigBuilder
from cmk.testlib.agent_receiver.site_mock import SiteMock, User
from cmk.testlib.agent_receiver.tasks import add_tasks, get_all_tasks
from cmk.testlib.agent_receiver.wiremock import Wiremock


def _setup(
    wiremock: Wiremock,
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    max_pending_tasks_per_relay: int,
) -> tuple[SiteMock, AgentReceiverClient, str]:
    site_name = "my_component_test_site"
    ar_site = AgentReceiverConfigBuilder(
        omd_root=tmp_path / site_name,
        site_name=site_name,
        apache_address=wiremock.wiremock_hostname,
        apache_port=wiremock.port,
        max_pending_tasks_per_relay=max_pending_tasks_per_relay,
    ).build()
    for key, value in ar_site.env.items():
        monkeypatch.setenv(key, value)
    get_config.cache_clear()

    user = User("testmo", "supersecret")
    wiremock.reset()
    site = SiteMock(
        wiremock, site_name, user, ar_site.internal_credentials, ar_site.config.omd_root
    )

    app = main_app()
    app.dependency_overrides[get_forward_monitoring_data_handler] = lambda config: (
        ForwardMonitoringDataHandler(data_socket=config.raw_data_socket, socket_timeout=2.0)
    )
    client = TestClient(app)
    agent_receiver = AgentReceiverClient(client, site_name, user)

    return site, agent_receiver, site_name


def test_cannot_push_more_pending_tasks_than_allowed(
    wiremock: Wiremock,
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify that pushing more tasks than the maximum allowed is rejected with a FORBIDDEN status.

    Test steps:
    1. Configure relay with max task limit and push to limit
    2. Attempt to push additional task
    3. Verify request is rejected with FORBIDDEN status
    """
    task_count = 3
    site, agent_receiver, site_name = _setup(
        wiremock, tmp_path, monkeypatch, max_pending_tasks_per_relay=task_count
    )

    relay_id = add_relays(site, 1)[0]
    agent_receiver.apply_config(site.push_config([relay_id]))

    # add maximum number of tasks allowed

    task_ids = add_tasks(task_count, agent_receiver, relay_id, site_name)

    # An additional task cannot be pushed

    with agent_receiver.with_client_ip("127.0.0.1"):
        response = agent_receiver.push_task(
            relay_id=relay_id,
            spec=FetchAdHocTask(payload=".."),
            site_cn=site_name,
        )

    assert response.status_code == HTTPStatus.FORBIDDEN, response.text
    assert response.json() == {
        "detail": f"The maximum number of tasks {task_count} has been reached"
    }

    # The list of tasks is unchanged

    current_tasks = {str(t.id) for t in get_all_tasks(agent_receiver, relay_id)}
    assert current_tasks == set(task_ids)


def test_cannot_push_more_tasks_after_marking_a_task_as_finished(
    wiremock: Wiremock,
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify that after marking a task as finished, new tasks can be pushed even when the limit was previously reached.

    Test steps:
    1. Push tasks to limit and mark one as finished
    2. Attempt to push new task
    3. Verify new task is accepted successfully
    """
    task_count = 3
    site, agent_receiver, site_name = _setup(
        wiremock, tmp_path, monkeypatch, max_pending_tasks_per_relay=task_count
    )

    relay_id = add_relays(site, 1)[0]
    agent_receiver.apply_config(site.push_config([relay_id]))

    # add maximum number of tasks allowed
    task_id, *_ = add_tasks(task_count, agent_receiver, relay_id, site_name)

    agent_receiver.update_task(
        relay_id=relay_id,
        task_id=task_id,
        result_type="OK",
        result_payload="done",
    )

    with agent_receiver.with_client_ip("127.0.0.1"):
        response = agent_receiver.push_task(
            relay_id=relay_id,
            spec=FetchAdHocTask(payload=".."),
            site_cn=site_name,
        )

    assert response.status_code == HTTPStatus.OK, response.text

    current_tasks = {str(t.id) for t in get_all_tasks(agent_receiver, relay_id)}
    assert len(current_tasks) == task_count + 1


def test_each_relay_has_its_own_limit(
    wiremock: Wiremock,
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify that each relay has its own independent task limit and filling one relay does not affect others.

    Test steps:
    1. Fill relay A to task limit
    2. Push task to relay B
    3. Verify relay B accepts task despite relay A being full
    """
    task_count = 5
    site, agent_receiver, site_name = _setup(
        wiremock, tmp_path, monkeypatch, max_pending_tasks_per_relay=task_count
    )

    relay_id_A, relay_id_B = add_relays(site, 2)

    # add maximum number of tasks allowed to relay A

    _ = add_tasks(task_count, agent_receiver, relay_id_A, site_name)

    # we should still be able to add tasks to relay B

    with agent_receiver.with_client_ip("127.0.0.1"):
        response = agent_receiver.push_task(
            relay_id=relay_id_B,
            spec=FetchAdHocTask(payload=".."),
            site_cn=site_name,
        )
    assert response.status_code == HTTPStatus.OK, response.text


def add_relays(site: SiteMock, count: int) -> list[str]:
    assert count > 0
    relay_ids = [str(uuid.uuid4()) for _ in range(count)]
    site.set_scenario(relay_ids)
    return relay_ids
