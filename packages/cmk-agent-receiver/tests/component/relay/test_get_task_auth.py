#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Tests for get-task endpoint authorization (localhost + CN validation)."""

from __future__ import annotations

import uuid
from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient

from cmk.relay_protocols.tasks import FetchAdHocTask
from cmk.testlib.agent_receiver.clients import SiteClient
from cmk.testlib.agent_receiver.site_mock import SiteMock


@pytest.mark.parametrize(
    "invalid_cn,description",
    [
        ("missing: no client certificate provided", "TLS connection without client cert"),
        ("", "empty CN"),
        ("wrongsite", "different cert CN"),
    ],
)
def test_get_task_with_various_invalid_cns(
    site: SiteMock,
    test_client: TestClient,
    invalid_cn: str,
    description: str,
) -> None:
    """Verify get-task rejects various invalid CN values.

    Expected: 403 Forbidden for all invalid CN values

    Steps:
    1. Start AR with configured relays
    2. Send get-task from localhost with invalid CN
    3. Verify request is rejected with 403
    """
    relay_id = str(uuid.uuid4())
    site.set_scenario([relay_id])

    site.push_config([relay_id])

    client_invalid = SiteClient(test_client, site.site_name, cn=invalid_cn)
    response = client_invalid.get_task(relay_id=relay_id, task_id=str(uuid.uuid4()))

    assert response.status_code == HTTPStatus.FORBIDDEN, (
        f"Expected 403 for {description} (CN: {invalid_cn!r}), got {response.status_code}: {response.text}"
    )
    assert "does not match local site CN" in response.text, (
        f"Expected error message for {description}, got: {response.text}"
    )


def test_get_task_with_valid_cn_and_localhost(
    site: SiteMock,
    test_client: TestClient,
) -> None:
    """Verify get-task succeeds with correct CN and localhost.

    Expected: 200 OK

    Steps:
    1. Start AR with configured relays and create a task
    2. Send get-task from localhost with correct site CN
    3. Verify request succeeds
    """
    relay_id = str(uuid.uuid4())
    site.set_scenario([relay_id])

    site.push_config([relay_id])

    # Create a task first
    site_ops = SiteClient(test_client, site.site_name)
    task_resp = site_ops.push_task(relay_id, FetchAdHocTask(payload=".."))
    assert task_resp.status_code == HTTPStatus.OK
    task_id = task_resp.json()["task_id"]

    client = SiteClient(test_client, site.site_name)
    response = client.get_task(relay_id=relay_id, task_id=task_id)

    assert response.status_code == HTTPStatus.OK, response.text


def test_get_task_cn_check_without_localhost(
    site: SiteMock,
    test_client: TestClient,
) -> None:
    """Verify get-task requires localhost even with valid CN.

    Expected: 403 Forbidden (localhost check fails first)

    Steps:
    1. Start AR with configured relays
    2. Send get-task from non-localhost IP with correct CN
    3. Verify request is rejected (localhost validation fails first)
    """
    relay_id = str(uuid.uuid4())
    site.set_scenario([relay_id])

    site.push_config([relay_id])

    client_remote = SiteClient(test_client, site.site_name, source_ip="192.168.1.100")
    response = client_remote.get_task(
        relay_id=relay_id,
        task_id=str(uuid.uuid4()),
    )

    assert response.status_code == HTTPStatus.FORBIDDEN, response.text
    assert "Request must originate from localhost" in response.text
