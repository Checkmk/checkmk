#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.collection.rulesets.apache_status import migrate


@pytest.mark.parametrize(
    "old, expected",
    [
        pytest.param(
            ("autodetect", [443]),
            {"deployment": ("sync", None), "instances": ("autodetect", [443])},
            id="old_autodetect",
        ),
        pytest.param(
            (
                "static",
                [(("http", None), "127.0.0.1", 80, "hurz")],
            ),
            {
                "deployment": ("sync", None),
                "instances": (
                    "static",
                    [{"protocol": "http", "address": "127.0.0.1", "port": 80, "instance": "hurz"}],
                ),
            },
            id="old_static_http",
        ),
        pytest.param(
            (
                "static",
                [(("https", "/etc/ssl/certs/cert.pem"), "10.0.0.1", 443, "secure")],
            ),
            {
                "deployment": ("sync", None),
                "instances": (
                    "static",
                    [
                        {
                            "protocol": "https",
                            "cafile": "/etc/ssl/certs/cert.pem",
                            "address": "10.0.0.1",
                            "port": 443,
                            "instance": "secure",
                        }
                    ],
                ),
            },
            id="old_static_https_with_cert",
        ),
        pytest.param(
            (
                "static",
                [(("https", None), "10.0.0.1", 443, "secure")],
            ),
            {
                "deployment": ("sync", None),
                "instances": (
                    "static",
                    [
                        {
                            "protocol": "https",
                            "address": "10.0.0.1",
                            "port": 443,
                            "instance": "secure",
                        }
                    ],
                ),
            },
            id="old_static_https_no_cert",
        ),
        pytest.param(
            None,
            {"deployment": ("do_not_deploy", None)},
            id="old_do_not_deploy",
        ),
        pytest.param(
            {"deployment": ("sync", None), "instances": ("autodetect", [443])},
            {"deployment": ("sync", None), "instances": ("autodetect", [443])},
            id="already_migrated",
        ),
    ],
)
def test_migrate(old: object, expected: dict[str, object]) -> None:
    assert migrate(old) == expected
