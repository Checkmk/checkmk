#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import uuid
from http import HTTPMethod

import httpx

from cmk.relay_protocols.tasks import TaskType

from .test_lib.relay_proxy import RelayProxy
from .test_lib.relays import register_relay
from .test_lib.site_mock import SiteMock
from .test_lib.tasks import get_all_relay_tasks, push_task


def test_a_relay_can_be_registered(relay_proxy: RelayProxy) -> None:
    """
    Register a relay and check if we can obtain a list of pending tasks for it.
    """

    relay_id_A = str(uuid.uuid4())
    register_relay(relay_id_A, relay_proxy)

    tasks_A = get_all_relay_tasks(relay_proxy, relay_id_A)
    assert len(tasks_A.tasks) == 0


def test_registering_a_relay_does_not_affect_other_relays(relay_proxy: RelayProxy) -> None:
    relay_id_A = str(uuid.uuid4())
    register_relay(relay_id_A, relay_proxy)
    push_task(
        relay_proxy=relay_proxy,
        relay_id=relay_id_A,
        task_type=TaskType.FETCH_AD_HOC,
        task_payload="any payload",
    )

    relay_id_B = str(uuid.uuid4())
    register_relay(relay_id_B, relay_proxy)

    tasks_A = get_all_relay_tasks(relay_proxy, relay_id_A)
    assert len(tasks_A.tasks) == 1


def test_contact_site(site: SiteMock) -> None:
    site.wiremock.base_url
    _ = httpx.get(f"{site.wiremock.base_url}/foo")
    reqs = site.wiremock.get_all_url_path_requests("/foo", HTTPMethod.GET)
    assert len(reqs) == 1
