#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.plugins.mqtt.rulesets.special_agent import _migrate_instance_and_client_id


@pytest.mark.parametrize(
    "old_rule, migrated_rule",
    [
        pytest.param(
            {
                "username": "admin",
                "password": ("store", "password_mqtt"),
                "address": "1.2.3.4",
                "port": 1883,
                "client-id": "ABCD",
                "protocol": "MQTTv311",
                "instance-id": "broker",
            },
            {
                "address": "1.2.3.4",
                "client_id": "ABCD",
                "instance_id": "broker",
                "password": (
                    "store",
                    "password_mqtt",
                ),
                "port": 1883,
                "protocol": "MQTTv311",
                "username": "admin",
            },
            id="all_arguments",
        ),
        pytest.param(
            {
                "username": "admin",
                "password": ("store", "password_mqtt"),
                "address": "1.2.3.4",
                "port": 1883,
                "protocol": "MQTTv311",
                "instance-id": "broker",
            },
            {
                "username": "admin",
                "password": ("store", "password_mqtt"),
                "address": "1.2.3.4",
                "port": 1883,
                "protocol": "MQTTv311",
                "instance_id": "broker",
            },
            id="only instance-id",
        ),
        pytest.param(
            {
                "username": "admin",
                "password": ("store", "password_mqtt"),
                "address": "1.2.3.4",
                "port": 1883,
                "protocol": "MQTTv311",
                "client-id": "ABCD",
            },
            {
                "username": "admin",
                "password": ("store", "password_mqtt"),
                "address": "1.2.3.4",
                "port": 1883,
                "protocol": "MQTTv311",
                "client_id": "ABCD",
            },
            id="only client-id",
        ),
        pytest.param(
            {
                "username": "admin",
                "password": ("store", "password_mqtt"),
                "address": "1.2.3.4",
                "port": 1883,
                "protocol": "MQTTv311",
            },
            {
                "username": "admin",
                "password": ("store", "password_mqtt"),
                "address": "1.2.3.4",
                "port": 1883,
                "protocol": "MQTTv311",
            },
            id="without instance-id and client-id",
        ),
    ],
)
def test_migrate_instance_and_client_id(
    old_rule: Mapping[str, object],
    migrated_rule: Mapping[str, object],
) -> None:
    assert _migrate_instance_and_client_id(old_rule) == migrated_rule
