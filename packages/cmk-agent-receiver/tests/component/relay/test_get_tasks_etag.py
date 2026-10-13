#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import uuid
from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient

from cmk.relay_protocols.tasks import HEADERS
from cmk.testlib.agent_receiver.clients import RelayClient, SiteClient
from cmk.testlib.agent_receiver.site_mock import SiteMock


def test_get_tasks_with_matching_etag_returns_not_modified(
    relay_id: str,
    site: SiteMock,
    test_client: TestClient,
) -> None:
    relay = RelayClient(test_client, site.site_name, relay_id)
    relay.apply_config(site.push_config([relay_id]))
    SiteClient(test_client, site.site_name).add_tasks(1, relay_id)
    etag = relay.get_tasks(status="PENDING").headers["ETag"]

    response = relay.get_tasks(status="PENDING", if_none_match=etag)

    assert response.status_code == HTTPStatus.NOT_MODIFIED, response.text
    assert response.content == b""
    assert response.headers["ETag"] == etag
    assert response.headers[HEADERS.VERSION] == "some.detailed.version"


def test_get_tasks_with_stale_etag_returns_changed_task_list(
    relay_id: str,
    site: SiteMock,
    test_client: TestClient,
) -> None:
    relay = RelayClient(test_client, site.site_name, relay_id)
    relay.apply_config(site.push_config([relay_id]))
    site_client = SiteClient(test_client, site.site_name)
    site_client.add_tasks(1, relay_id)
    stale_etag = relay.get_tasks(status="PENDING").headers["ETag"]
    (new_task_id,) = site_client.add_tasks(1, relay_id)

    response = relay.get_tasks(status="PENDING", if_none_match=stale_etag)

    assert response.status_code == HTTPStatus.OK, response.text
    assert new_task_id in {task["id"] for task in response.json()["tasks"]}
    assert response.headers["ETag"] != stale_etag


def test_get_tasks_after_task_update_returns_changed_task_list(
    relay_id: str,
    site: SiteMock,
    test_client: TestClient,
) -> None:
    relay = RelayClient(test_client, site.site_name, relay_id)
    relay.apply_config(site.push_config([relay_id]))
    (task_id,) = SiteClient(test_client, site.site_name).add_tasks(1, relay_id)
    stale_etag = relay.get_tasks().headers["ETag"]
    relay.update_task(task_id=task_id, result_type="OK", result_payload="done")

    response = relay.get_tasks(if_none_match=stale_etag)

    assert response.status_code == HTTPStatus.OK, response.text
    assert {task["id"]: task["status"] for task in response.json()["tasks"]}[task_id] == "FINISHED"
    assert response.headers["ETag"] != stale_etag


@pytest.fixture
def relay_id(site: SiteMock) -> str:
    relay_id = str(uuid.uuid4())
    site.set_scenario(relay_id)
    return relay_id
