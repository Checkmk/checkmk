#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from http import HTTPStatus

from fastapi.testclient import TestClient

from cmk.relay_protocols.tasks import FetchAdHocTask
from cmk.testlib.agent_receiver.clients import (
    RelayClient,
    RelayRegistrationClient,
    SiteClient,
)
from cmk.testlib.agent_receiver.relay import random_relay_id
from cmk.testlib.agent_receiver.site_mock import OP, SiteMock, User


def test_create_task_unknown_relay(
    test_client: TestClient,
    site: SiteMock,
    user: User,
) -> None:
    """Verify that tasks can be created for unknown relay IDs as the site is responsible for handling such cases.

    Test steps:
    1. Register relay and configure agent receiver
    2. Push task to unknown relay ID
    3. Verify task is created successfully
    """
    # We allow creating tasks for unknown relays. For now it's the site's responsibility
    # to handle such cases.
    relay_id = random_relay_id()
    site.set_scenario([], [(relay_id, OP.ADD)])
    reg = RelayRegistrationClient(test_client, site.site_name)
    reg.register("relay1", relay_id, user)

    relay = RelayClient(test_client, site.site_name, relay_id)
    relay.apply_config(site.push_config([relay_id]))

    client = SiteClient(test_client, site.site_name)
    response = client.push_task("bad_relay_id", FetchAdHocTask(payload=".."))
    assert response.status_code == HTTPStatus.OK
    assert response.json()["task_id"] is not None
