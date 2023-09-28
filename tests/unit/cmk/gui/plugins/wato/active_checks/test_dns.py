#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.gui.plugins.wato.active_checks.dns import _migrate


@pytest.mark.parametrize(
    "params, result",
    [
        [
            (
                "google.de",
                {},
            ),
            {
                "hostname": "google.de",
                "server": None,
            },
        ],
        [
            (
                "google.de",
                {"expected_address": "1.2.3.4,C0FE::FE11"},
            ),
            {
                "hostname": "google.de",
                "server": None,
                "expect_all_addresses": True,
                "expected_addresses_list": ["1.2.3.4", "C0FE::FE11"],
            },
        ],
        [
            (
                "google.de",
                {
                    "expected_address": "1.2.3.4,C0FE::FE11",
                    "server": "127.0.0.53",
                    "timeout": 10,
                    "response_time": (1.0, 2.0),
                    "expected_authority": True,
                },
            ),
            {
                "hostname": "google.de",
                "expect_all_addresses": True,
                "expected_addresses_list": ["1.2.3.4", "C0FE::FE11"],
                "server": "127.0.0.53",
                "timeout": 10,
                "response_time": (1.0, 2.0),
                "expected_authority": True,
            },
        ],
        [
            (
                "google.de",
                {
                    "expected_addresses_list": ["1.2.3.4", "C0FE::FE11"],
                    "server": "127.0.0.53",
                    "timeout": 10,
                    "response_time": (1.0, 2.0),
                    "expected_authority": True,
                },
            ),
            {
                "hostname": "google.de",
                "expected_addresses_list": ["1.2.3.4", "C0FE::FE11"],
                "server": "127.0.0.53",
                "timeout": 10,
                "response_time": (1.0, 2.0),
                "expected_authority": True,
            },
        ],
    ],
)
def test_legacy_params(
    params: Mapping[str, object] | tuple[str, Mapping[str, object]], result: Mapping[str, object]
) -> None:
    assert _migrate(params) == result
