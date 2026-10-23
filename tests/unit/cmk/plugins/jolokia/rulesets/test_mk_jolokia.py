#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.jolokia.rulesets.mk_jolokia import migrate

_NEW = {
    "deployment": "sync",
    "main_instance": {"port": 9090, "instance": "jvm"},
    "instances": [{"port": 9091}],
}


@pytest.mark.parametrize(
    "old, expected",
    [
        pytest.param(
            None,
            {"deployment": "do_not_deploy", "main_instance": {}, "instances": []},
            id="do_not_deploy",
        ),
        pytest.param(
            {},
            {"deployment": "sync", "main_instance": {}, "instances": []},
            id="old_empty",
        ),
        pytest.param(
            {
                "server": "10.0.0.1",
                "login": ("u", ("store", "pw_id"), "basic"),
                "instance": "jvm",
                "port": 9090,
                "instances": [{"server": None, "port": 9091}],
            },
            {
                "deployment": "sync",
                "main_instance": {
                    "server": ("ip_or_fqdn", "10.0.0.1"),
                    "login": {
                        "user": "u",
                        "password": ("cmk_postprocessed", "stored_password", ("pw_id", "")),
                        "mode": "basic",
                    },
                    "instance": "jvm",
                    "port": 9090,
                },
                "instances": [{"server": ("use_local_fqdn", None), "port": 9091}],
            },
            id="old_with_login_and_instances",
        ),
        pytest.param(_NEW, _NEW, id="new"),
    ],
)
def test_migrate(old: object, expected: dict[str, object]) -> None:
    assert migrate(old) == expected


def test_migrate_rejects_unknown_values() -> None:
    with pytest.raises(ValueError):
        migrate("unexpected")


def test_migrate_login_with_explicit_password() -> None:
    migrated = migrate({"login": ("monitoring", ("password", "secret"), "digest")})
    match migrated["main_instance"]:
        case {
            "login": {
                "user": "monitoring",
                "password": ("cmk_postprocessed", "explicit_password", (str(), "secret")),
                "mode": "digest",
            }
        }:
            pass
        case other:
            raise AssertionError(other)
