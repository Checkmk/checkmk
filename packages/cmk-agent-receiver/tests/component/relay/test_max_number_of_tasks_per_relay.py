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
from cmk.testlib.agent_receiver.builder import AgentReceiverConfigBuilder
from cmk.testlib.agent_receiver.clients import RelayClient, SiteClient
from cmk.testlib.agent_receiver.site_mock import SiteMock, User
from cmk.testlib.agent_receiver.wiremock import Wiremock


def _setup(
    wiremock: Wiremock,
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    max_pending_tasks_per_relay: int,
) -> tuple[SiteMock, TestClient]:
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

    return site, client


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
    site, test_client = _setup(
        wiremock, tmp_path, monkeypatch, max_pending_tasks_per_relay=task_count
    )

    relay_id = add_relays(site, 1)[0]

    relay = RelayClient(test_client, site.site_name, relay_id)
    relay.apply_config(site.push_config([relay_id]))

    # add maximum number of tasks allowed
    site_c = SiteClient(test_client, site.site_name)
    task_ids = site_c.add_tasks(task_count, relay_id)

    # An additional task cannot be pushed
    response = site_c.push_task(relay_id, FetchAdHocTask(payload=".."))

    assert response.status_code == HTTPStatus.FORBIDDEN, response.text
    assert response.json() == {
        "detail": f"The maximum number of tasks {task_count} has been reached"
    }

    # The list of tasks is unchanged
    current_tasks = {str(t.id) for t in relay.get_task_list().tasks}
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
    site, test_client = _setup(
        wiremock, tmp_path, monkeypatch, max_pending_tasks_per_relay=task_count
    )

    relay_id = add_relays(site, 1)[0]

    relay = RelayClient(test_client, site.site_name, relay_id)
    relay.apply_config(site.push_config([relay_id]))

    # add maximum number of tasks allowed
    site_c = SiteClient(test_client, site.site_name)
    task_id, *_ = site_c.add_tasks(task_count, relay_id)

    relay.update_task(
        task_id=task_id,
        result_type="OK",
        result_payload="done",
    )

    response = site_c.push_task(relay_id, FetchAdHocTask(payload=".."))

    assert response.status_code == HTTPStatus.OK, response.text

    current_tasks = {str(t.id) for t in relay.get_task_list().tasks}
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
    site, test_client = _setup(
        wiremock, tmp_path, monkeypatch, max_pending_tasks_per_relay=task_count
    )

    relay_id_A, relay_id_B = add_relays(site, 2)

    # add maximum number of tasks allowed to relay A
    site_c = SiteClient(test_client, site.site_name)
    _ = site_c.add_tasks(task_count, relay_id_A)

    # we should still be able to add tasks to relay B
    response = site_c.push_task(relay_id_B, FetchAdHocTask(payload=".."))
    assert response.status_code == HTTPStatus.OK, response.text


def add_relays(site: SiteMock, count: int) -> list[str]:
    assert count > 0
    relay_ids = [str(uuid.uuid4()) for _ in range(count)]
    site.set_scenario(relay_ids)
    return relay_ids
