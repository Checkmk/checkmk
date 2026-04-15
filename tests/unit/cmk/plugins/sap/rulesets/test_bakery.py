#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.plugins.legacy_bakery_rulesets.mk_sap import migrate, migrate_instance

INSTANCES = [
    {
        "ashost": "localhost",
        "sysnr": "00",
        "client": "100",
        "user": "cmk-user",
        "passwd": ("cmk_postprocessed", "explicit_password", ("some-uuid", "secret")),
        "trace": "3",
        "lang": "EN",
    }
]

PATHS = [
    "SAP BI Monitors/BI Monitor",
    "SAP CCMS Monitor Templates/Operating System/OperatingSystem/CPU/*",
]


@pytest.mark.parametrize(
    "old, expected",
    [
        pytest.param(
            None,
            {"deployment": ("do_not_deploy", None)},
            id="do_not_deploy",
        ),
        pytest.param(
            {"instances": INSTANCES, "paths": PATHS},
            {"deployment": ("sync", None), "instances": INSTANCES, "paths": PATHS},
            id="deploy_with_config",
        ),
        pytest.param(
            {"deployment": ("sync", None), "instances": INSTANCES, "paths": PATHS},
            {"deployment": ("sync", None), "instances": INSTANCES, "paths": PATHS},
            id="already_migrated_sync",
        ),
        pytest.param(
            {"deployment": ("do_not_deploy", None)},
            {"deployment": ("do_not_deploy", None)},
            id="already_migrated_do_not_deploy",
        ),
        pytest.param(
            {"deployment": ("cached", 3600.0)},
            {"deployment": ("cached", 3600.0)},
            id="already_migrated_cached",
        ),
    ],
)
def test_migrate(old: object, expected: dict[str, object]) -> None:
    assert migrate(old) == expected


def test_migrate_instance_already_migrated() -> None:
    value = {
        "user": "cmk-user",
        "passwd": ("cmk_postprocessed", "explicit_password", ("some-uuid", "secret")),
    }
    assert migrate_instance(value) == value


def test_migrate_instance_old_password_format() -> None:
    result = migrate_instance({"user": "cmk-user", "passwd": ("password", "secret")})
    assert isinstance(result, dict)
    passwd = result["passwd"]
    assert isinstance(passwd, tuple)
    assert passwd[0] == "cmk_postprocessed"
    assert passwd[1] == "explicit_password"
    assert isinstance(passwd[2], tuple)
    assert passwd[2][1] == "secret"


def test_migrate_instance_stored_password_format() -> None:
    result = migrate_instance({"user": "cmk-user", "passwd": ("store", "my-store-id")})
    assert isinstance(result, dict)
    passwd = result["passwd"]
    assert isinstance(passwd, tuple)
    assert passwd[0] == "cmk_postprocessed"
    assert passwd[1] == "stored_password"
    assert isinstance(passwd[2], tuple)
    assert passwd[2][0] == "my-store-id"
