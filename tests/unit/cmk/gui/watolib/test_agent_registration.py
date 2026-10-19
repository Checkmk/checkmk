#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from uuid import UUID

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.gui.watolib.agent_registration import (
    link_uuid_of_existing_host,
    link_uuid_of_registration,
    UUIDAlreadyLinkedError,
)
from tests.testlib.unit.fake_site import LoggedSecurityEvent


def test_a_refused_registration_of_a_linked_uuid_writes_a_security_event(
    security_events: list[LoggedSecurityEvent],
) -> None:
    """CMK-40803 AC-2"""
    uuid = UUID("1409ac78-6548-4138-9285-12484409ddf2")
    link_uuid_of_registration(HostName("heute"), uuid, push_configured=False)

    with pytest.raises(UUIDAlreadyLinkedError):
        link_uuid_of_existing_host(HostName("my-host"), uuid, push_configured=False)

    assert [
        event.details
        for event in security_events
        if event.summary == "registration of a linked UUID refused"
    ] == [{"host_name": "my-host", "uuid": str(uuid), "linked_host_name": "heute"}]
