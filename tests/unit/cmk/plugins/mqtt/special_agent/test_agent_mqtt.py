#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.plugins.mqtt.special_agent import agent_mqtt


def test_parse_minimal_arguments() -> None:
    args = agent_mqtt.parse_arguments(
        [
            "address",
        ]
    )
    assert args.address == "address"
    assert args.port == 1883
    assert args.protocol == "MQTTv311"
    assert args.username is None
    assert args.password is None
    assert args.client_id is None


def test_parse_all_arguments() -> None:
    args = agent_mqtt.parse_arguments(
        [
            "--username",
            "asd",
            "--password",
            "xyz",
            "--port",
            "1337",
            "--protocol",
            "MQTTv5",
            "--client-id",
            "ding",
            "addr",
        ]
    )
    assert args.address == "addr"
    assert args.port == 1337
    assert args.protocol == "MQTTv5"
    assert args.username == "asd"
    assert args.password.reveal() == "xyz"
    assert args.client_id == "ding"
