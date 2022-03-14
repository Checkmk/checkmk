#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping, Sequence

import pytest

from tests.testlib import SpecialAgent

from cmk.utils import password_store

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    "params, expected_result",
    [
        pytest.param(
            {
                "username": "asd",
                "password": ("password", "xyz"),
                "address": "addr",
                "port": 1337,
                "client-id": "ding",
                "protocol": "MQTTv5",
            },
            [
                "--client-id",
                "ding",
                "--password",
                "xyz",
                "--port",
                "1337",
                "--protocol",
                "MQTTv5",
                "--username",
                "asd",
                "addr",
            ],
            id="all_arguments",
        ),
        pytest.param(
            {
                "password": ("store", "mqtt_password"),
            },
            ["--password", ("store", "mqtt_password", "%s"), "address"],
            id="with_password_store",
        ),
        pytest.param(
            {},
            ["address"],
            id="minimal_arguments",
        ),
    ],
)
def test_mqtt_argument_parsing(
    params: Mapping[str, Any],
    expected_result: Sequence[str],
) -> None:
    password_store.save({"mqtt_password": "blablu"})
    assert (
        SpecialAgent("agent_mqtt").argument_func(
            params,
            "testhost",
            "address",
        )
        == expected_result
    )
