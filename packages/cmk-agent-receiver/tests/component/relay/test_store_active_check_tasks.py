#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import uuid
from http import HTTPStatus

from fastapi.testclient import TestClient

from cmk.relay_protocols.tasks import AdHocActiveCheckTask, TaskStatus
from cmk.testlib.agent_receiver.clients import RelayClient, SiteClient
from cmk.testlib.agent_receiver.site_mock import SiteMock


def test_store_ad_hoc_active_check_task(
    test_client: TestClient,
    site: SiteMock,
) -> None:
    """A relay must receive an ad-hoc active check it is asked to run.

    Test steps:
    1. Create an ad-hoc active-check task for a relay
    2. Let the relay poll its tasks
    3. Verify the task comes back with the command to run
    """
    relay_id = str(uuid.uuid4())
    site.set_scenario(relay_id)

    relay = RelayClient(test_client, site.site_name, relay_id)
    relay.apply_config(site.push_config([relay_id]))

    SiteClient(test_client, site.site_name).create_task(
        relay_id, AdHocActiveCheckTask(host="myhost", command="check_icmp 1.2.3.4", timeout=30.0)
    )

    tasks = relay.get_task_list()

    assert len(tasks.tasks) == 1
    spec = tasks.tasks[0].spec
    assert isinstance(spec, AdHocActiveCheckTask)
    assert spec.host == "myhost"
    assert spec.command == "check_icmp 1.2.3.4"
    assert spec.timeout == 30.0


def test_report_the_result_of_an_ad_hoc_active_check(
    test_client: TestClient,
    site: SiteMock,
) -> None:
    """A relay reports the check's output through the normal task-update endpoint.

    Test steps:
    1. Create an ad-hoc active-check task and let the relay poll it
    2. Report a result for it
    3. Verify the task is finished and carries the reported output
    """
    relay_id = str(uuid.uuid4())
    site.set_scenario(relay_id)

    relay = RelayClient(test_client, site.site_name, relay_id)
    relay.apply_config(site.push_config([relay_id]))

    site_client = SiteClient(test_client, site.site_name)
    task_id = site_client.create_task(
        relay_id, AdHocActiveCheckTask(host="myhost", command="check_icmp 1.2.3.4")
    ).task_id

    frame = "000\n0000000f\nmyhost\tOK - 1.2.3.4 responds"
    response = relay.update_task(task_id, result_type="OK", result_payload=frame)

    assert response.status_code == HTTPStatus.ACCEPTED, response.text
    updated = relay.get_task_list().tasks[0]
    assert updated.status is TaskStatus.FINISHED
    assert updated.result_payload == frame
