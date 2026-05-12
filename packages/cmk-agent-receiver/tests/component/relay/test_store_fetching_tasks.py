#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import uuid
from http import HTTPStatus

from fastapi.testclient import TestClient

from cmk.relay_protocols.tasks import FetchAdHocTask
from cmk.testlib.agent_receiver.clients import RelayClient, SiteClient
from cmk.testlib.agent_receiver.site_mock import SiteMock


def test_store_fetching_task(
    test_client: TestClient,
    site: SiteMock,
) -> None:
    """Verify that a fetching task can be stored and later retrieved with the correct payload.

    Test steps:
    1. Push a fetching task to a relay
    2. Retrieve relay tasks
    3. Verify task is stored with correct payload
    """
    relay_id = str(uuid.uuid4())
    site.set_scenario(relay_id)

    relay = RelayClient(test_client, site.site_name, relay_id)
    relay.apply_config(site.push_config([relay_id]))

    site_c = SiteClient(test_client, site.site_name)
    site_c.create_task(relay_id, FetchAdHocTask(payload="any payload"))

    tasks_1 = relay.get_task_list()
    assert len(tasks_1.tasks) == 1
    assert isinstance(tasks_1.tasks[0].spec, FetchAdHocTask)
    assert tasks_1.tasks[0].spec.payload == "any payload"


def test_store_fetching_tasks_does_not_affect_other_relays(
    test_client: TestClient,
    site: SiteMock,
) -> None:
    """Verify that storing tasks for one relay does not affect the tasks of other relays.

    Test steps:
    1. Push tasks to relay A
    2. Verify relay B has no tasks
    3. Verify relay A maintains its tasks independently
    """
    relay_id_A = str(uuid.uuid4())
    relay_id_B = str(uuid.uuid4())
    site.set_scenario([relay_id_A, relay_id_B])

    relay_a = RelayClient(test_client, site.site_name, relay_id_A)
    relay_a.apply_config(site.push_config([relay_id_A, relay_id_B]))

    site_c = SiteClient(test_client, site.site_name)
    site_c.create_task(relay_id_A, FetchAdHocTask(payload=".."))

    tasks_A = relay_a.get_task_list()
    assert len(tasks_A.tasks) == 1
    relay_b = RelayClient(test_client, site.site_name, relay_id_B)
    tasks_B = relay_b.get_task_list()
    assert len(tasks_B.tasks) == 0

    site_c.create_task(relay_id_A, FetchAdHocTask(payload=".."))

    tasks_A = relay_a.get_task_list()
    assert len(tasks_A.tasks) == 2
    assert tasks_A.tasks[1].id != tasks_A.tasks[0].id
    tasks_B = relay_b.get_task_list()
    assert len(tasks_B.tasks) == 0


def test_store_fetching_task_non_existent_relay(
    test_client: TestClient,
    site: SiteMock,
) -> None:
    """Verify that tasks can be stored for a relay even when the relay does not have a configured folder.

    Test steps:
    1. Push task to relay without configured folder
    2. Verify task is created successfully
    3. Verify task is retrievable with correct payload
    """
    relay_id = str(uuid.uuid4())
    site.set_scenario(relay_id)
    site.push_config([])

    site_c = SiteClient(test_client, site.site_name)
    response = site_c.push_task(relay_id, FetchAdHocTask(payload=".."))

    assert response.status_code == HTTPStatus.OK
    relay = RelayClient(test_client, site.site_name, relay_id)
    tasks = relay.get_task_list()
    assert len(tasks.tasks) == 1
    assert isinstance(tasks.tasks[0].spec, FetchAdHocTask)
    assert tasks.tasks[0].spec.payload == ".."
