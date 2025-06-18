#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.uniserv.server_side_calls.check_uniserv import active_check_uniserv
from cmk.server_side_calls.v1 import ActiveCheckCommand, HostConfig, IPv4Config


def test_parse_version():
    params = {
        "port": 123,
        "service": "foobar",
        "check_version": True,
        "check_address": ("no", None),
    }
    assert list(
        active_check_uniserv(
            params,
            HostConfig(name="test", ipv4_config=IPv4Config(address="address")),
        )
    ) == [
        ActiveCheckCommand(
            service_description="Uniserv foobar Version",
            command_arguments=("address", "123", "foobar", "VERSION"),
        )
    ]


def test_parse_address():
    params = {
        "port": 123,
        "service": "foobar",
        "check_version": False,
        "check_address": (
            "yes",
            {"street": "street", "street_no": 0, "city": "city", "search_regex": "regex"},
        ),
    }
    assert list(
        active_check_uniserv(
            params,
            HostConfig(name="test", ipv4_config=IPv4Config(address="address")),
        )
    ) == [
        ActiveCheckCommand(
            service_description="Uniserv foobar Address city",
            command_arguments=(
                "address",
                "123",
                "foobar",
                "ADDRESS",
                "street",
                "0",
                "city",
                "regex",
            ),
        )
    ]
