#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from cmk.utils import password_store

from cmk.plugins.mqtt.special_agent import agent_mqtt
from cmk.special_agents.v0_unstable.argument_parsing import Args


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


def test_parse_password_store(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    store_file = tmp_path / "store"
    password_store.save({"mqtt_password": "blablu"}, store_file)
    monkeypatch.setattr(
        "sys.argv",
        [
            "agent_mqtt",
            f"--pwstore=2@0@{store_file}@mqtt_password",
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
