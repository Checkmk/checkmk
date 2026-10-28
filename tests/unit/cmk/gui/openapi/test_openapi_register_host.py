#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import threading
from http import HTTPStatus
from uuid import uuid4

import pytest

import cmk.utils.paths
from cmk.gui.watolib.activate_changes import AutomationGetConfigSyncState
from cmk.utils.agent_registration import get_r4r_filepath, UUIDLinkManager
from tests.testlib.unit.fake_site import LoggedSecurityEvent
from tests.testlib.unit.rest_api_client import ClientRegistry


@pytest.mark.usefixtures("with_host")
def test_register_refuses_a_uuid_of_an_open_request(
    clients: ClientRegistry, security_events: list[LoggedSecurityEvent]
) -> None:
    """CMK-40803 AC5"""
    uuid = uuid4()
    cmk.utils.paths.r4r_new_dir.mkdir(parents=True)
    get_r4r_filepath(cmk.utils.paths.r4r_new_dir, uuid).write_text(
        json.dumps(
            {"uuid": str(uuid), "username": "my-username", "agent_labels": {}, "agent_cert": "cert"}
        )
    )

    resp = clients.HostConfig.register("example.com", str(uuid), expect_ok=False)

    resp.assert_status_code(HTTPStatus.CONFLICT)
    assert [
        event.details
        for event in security_events
        if event.summary == "registration of a UUID with an open request refused"
    ] == [{"host_name": "example.com", "uuid": str(uuid)}]
    assert not list(
        UUIDLinkManager(
            received_outputs_dir=cmk.utils.paths.received_outputs_dir,
            data_source_dir=cmk.utils.paths.data_source_push_agent_dir,
            r4r_discoverable_dir=cmk.utils.paths.r4r_discoverable_dir,
            uuid_lookup_dir=cmk.utils.paths.uuid_lookup_dir,
            registrations_dir=cmk.utils.paths.registrations_dir,
        )
    )


@pytest.mark.usefixtures("with_host")
def test_register_does_not_wait_for_the_setup_lock(
    clients: ClientRegistry, setup_lock_held_elsewhere: threading.Event
) -> None:
    """CMK-41457: A bulk discovery holds the lock for minutes."""
    clients.HostConfig.register("example.com", str(uuid4()))

    assert not setup_lock_held_elsewhere.is_set(), "The registration waited for the Setup lock"


@pytest.mark.usefixtures("with_host")
def test_register_leaves_the_config_generation_unchanged(clients: ClientRegistry) -> None:
    """A new config generation aborts a running config sync of the site."""
    _, generation_before = AutomationGetConfigSyncState().execute([])

    clients.HostConfig.register("example.com", str(uuid4()))

    assert AutomationGetConfigSyncState().execute([])[1] == generation_before
