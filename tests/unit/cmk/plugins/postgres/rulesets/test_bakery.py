#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

from typing import Any

import pytest

from cmk.plugins.postgres.rulesets.mk_postgres import (
    migrate,
    migrate_instance,
)

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


@pytest.mark.parametrize(
    "from_disk, expected",
    [
        pytest.param(
            {
                "instance_env_filepath": "",
                "instance_username": "",
                "instance_pgpass_filepath": "",
            },
            {
                "instance_name": "",
                "instance_env_filepath": "",
                "instance_username": "",
                "instance_pgpass_filepath": "",
            },
            id="Legacy II - missing instance_name",
        ),
    ],
)
def test_forth_outdated(from_disk: dict[str, Any], expected: object) -> None:
    got = migrate_instance(from_disk)
    assert got == expected


@pytest.mark.parametrize(
    "from_disk",
    [
        pytest.param(
            {
                "instance_name": "hi",
                "instance_env_filepath": "",
                "instance_username": "",
                "instance_pgpass_filepath": "",
            },
            id="single instance, non-empty name",
        ),
        pytest.param(
            {
                "instance_name": "",
                "instance_env_filepath": "",
                "instance_username": "",
                "instance_pgpass_filepath": "",
            },
            id="Empty instance name",
        ),
    ],
)
def test_forth_up_to_date(from_disk: dict[str, Any]) -> None:
    got = migrate_instance(from_disk)
    assert got == from_disk
