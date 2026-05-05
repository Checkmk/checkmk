#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.jar_signature.rulesets.bakery import migrate


def test_migrate_tuple() -> None:
    assert migrate(("/usr/lib/jvm", ["/opt/*.jar", "/srv/*.jar"])) == {
        "deployment": ("sync", None),
        "java_home": "/usr/lib/jvm",
        "paths": ["/opt/*.jar", "/srv/*.jar"],
    }


def test_migrate_list() -> None:
    assert migrate(["/usr/lib/jvm", ["/opt/*.jar"]]) == {
        "deployment": ("sync", None),
        "java_home": "/usr/lib/jvm",
        "paths": ["/opt/*.jar"],
    }


def test_migrate_none() -> None:
    assert migrate(None) == {"deployment": ("do_not_deploy", None)}


def test_migrate_already_migrated_sync() -> None:
    value = {
        "deployment": ("sync", None),
        "java_home": "/usr/lib/jvm",
        "paths": ["/opt/*.jar"],
    }
    assert migrate(value) == value


def test_migrate_already_migrated_do_not_deploy() -> None:
    value = {"deployment": ("do_not_deploy", None)}
    assert migrate(value) == value


def test_migrate_unexpected_raises() -> None:
    with pytest.raises(ValueError, match="Unexpected value"):
        migrate(42)
