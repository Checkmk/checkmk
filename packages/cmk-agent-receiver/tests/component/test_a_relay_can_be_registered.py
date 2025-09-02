#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import uuid
from http import HTTPMethod

import httpx

from .test_lib.relay_proxy import RelayProxy
from .test_lib.relays import register_relay
from .test_lib.site_mock import SiteMock
from .test_lib.tasks import get_all_relay_tasks


def test_a_relay_can_be_registered(relay_proxy: RelayProxy) -> None:
    """
    Test CT-1. Description:

    POST /relays/{relay_id_A}
    POST /relays/{relay_id_B}
    GET /relays/{relay_id_A}/tasks
    GET /relays/{relay_id_B}/tasks
    """

    relay_id_A = str(uuid.uuid4())
    register_relay(relay_id_A, relay_proxy)

    relay_id_B = str(uuid.uuid4())
    register_relay(relay_id_B, relay_proxy)

    # Verify both relays have tasks queue
    tasks_A = get_all_relay_tasks(relay_proxy, relay_id_A)
    assert len(tasks_A.tasks) == 0

    tasks_B = get_all_relay_tasks(relay_proxy, relay_id_B)
    assert len(tasks_B.tasks) == 0


def test_contact_site(site: SiteMock) -> None:
    site.wiremock.base_url
    _ = httpx.get(f"{site.wiremock.base_url}/foo")
    reqs = site.wiremock.get_all_url_path_requests("/foo", HTTPMethod.GET)
    assert len(reqs) == 1
