#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.password_store.v1_unstable import resolve_secret_option
from cmk.plugins.hivemanager_ng.special_agent import agent_hivemanager_ng


def test_parse_arguments() -> None:
    args = agent_hivemanager_ng.parse_arguments(
        ["https://api.extremecloudiq.com", "user", "--password", "secret"]
    )
    assert args.url == "https://api.extremecloudiq.com"
    assert args.username == "user"
    assert resolve_secret_option(args, agent_hivemanager_ng.SECRET_OPTION).reveal() == "secret"
    assert args.debug is False


def test_device_line_maps_extremecloudiq_fields() -> None:
    device = {
        "hostname": "Host-1",
        "connected": True,
        "active_clients": 14,
        "ip_address": "10.8.92.100",
        "serial_number": "00000000000001",
        "software_version": "10.6.1.0",
        "last_connect_time": "2026-06-12T10:01:43.674Z",
        # extra fields returned by the API must be ignored
        "id": 123456789,
        "mac_address": "AA:BB:CC:DD:EE:FF",
    }
    assert agent_hivemanager_ng.device_line(device) == (
        "hostName::Host-1|"
        "connected::True|"
        "activeClients::14|"
        "ip::10.8.92.100|"
        "serialId::00000000000001|"
        "osVersion::10.6.1.0|"
        "lastUpdated::2026-06-12T10:01:43.674Z"
    )


def test_device_line_handles_missing_fields() -> None:
    # A disconnected device without an active client count must not crash the agent
    # and is reported as not connected with zero clients.
    line = agent_hivemanager_ng.device_line({"hostname": "Host-2"})
    fields = dict(element.split("::", 1) for element in line.split("|"))
    assert fields["connected"] == "False"
    assert fields["activeClients"] == "0"
