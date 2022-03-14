#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils import password_store
from cmk.utils.config_path import LATEST_CONFIG

from cmk.special_agents import agent_mqtt
from cmk.special_agents.utils.argument_parsing import Args


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
    assert args.password == "xyz"
    assert args.client_id == "ding"


def test_parse_password_store(monkeypatch) -> None:
    password_store.save({"mqtt_password": "blablu"})
    password_store.save_for_helpers(LATEST_CONFIG)
    monkeypatch.setattr(
        "sys.argv",
        [
            "agent_mqtt",
            "--pwstore=2@0@mqtt_password",
            "--password",
            "******",
            "--username",
            "mqtt",
            "piff",
        ],
    )

    def test_main(args: Args) -> None:
        assert args.password == "blablu"

    monkeypatch.setattr(agent_mqtt, "agent_mqtt_main", test_main)

    agent_mqtt.main()
