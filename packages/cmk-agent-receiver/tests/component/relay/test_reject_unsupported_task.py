#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import uuid
from http import HTTPStatus

from fastapi.testclient import TestClient

from cmk.relay_protocols.tasks import AdHocActiveCheckTask
from cmk.testlib.agent_receiver.clients import SiteClient
from cmk.testlib.agent_receiver.site_mock import SiteMock


def test_creating_an_ad_hoc_active_check_task_is_rejected(
    test_client: TestClient,
    site: SiteMock,
) -> None:
    """The task type exists in the protocol, but this receiver cannot store it yet.

    It has to say so: silently storing it as a fetching task would send a relay a
    task it cannot run, and reporting success would hide that from the caller.
    """
    relay_id = str(uuid.uuid4())
    site.set_scenario(relay_id)

    response = SiteClient(test_client, site.site_name).push_task(
        relay_id, AdHocActiveCheckTask(host="myhost", command="check_icmp 1.2.3.4")
    )

    assert response.status_code == HTTPStatus.NOT_IMPLEMENTED, response.text
