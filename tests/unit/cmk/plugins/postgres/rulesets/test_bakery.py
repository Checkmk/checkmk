#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.plugins.postgres.rulesets.mk_postgres import migrate

_INSTANCES_SETTINGS = {
    "db_username": "postgres",
    "instances": [
        {
            "instance_env_filepath": "/home/postgres/db.env",
            "instance_name": "db",
            "instance_username": "postgres",
            "instance_pgpass_filepath": "/home/postgres/.pgpass",
        }
    ],
}


@pytest.mark.parametrize(
    "old, expected",
    [
        pytest.param(None, {"deployment": ("do_not_deploy", None)}, id="do_not_deploy"),
        pytest.param(
            {"instances_settings": _INSTANCES_SETTINGS},
            {"deployment": ("sync", None), "instances_settings": _INSTANCES_SETTINGS},
            id="old_config",
        ),
        pytest.param(
            {"deployment": ("cached", 300.0), "instances_settings": _INSTANCES_SETTINGS},
            {"deployment": ("cached", 300.0), "instances_settings": _INSTANCES_SETTINGS},
            id="already_migrated",
        ),
    ],
)
def test_migrate(old: object, expected: dict[str, object]) -> None:
    assert migrate(old) == expected
