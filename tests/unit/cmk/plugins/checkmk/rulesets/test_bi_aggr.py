#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.checkmk.rulesets.bi_aggr import migrate_credentials


def test_migrate_automation_already_migrated() -> None:
    assert migrate_credentials(("automation", None)) == ("automation", None)


def test_migrate_automation() -> None:
    assert migrate_credentials("automation") == ("automation", None)


def test_migrate_credentials_already_migrated() -> None:
    assert migrate_credentials(("credentials", {"user": "USER", "secret": "SECRET"})) == (
        "credentials",
        {"user": "USER", "secret": "SECRET"},
    )


def test_migrate_credentials() -> None:
    assert migrate_credentials(("credentials", ("USER", "SECRET"))) == (
        "credentials",
        {"user": "USER", "secret": "SECRET"},
    )


def test_migrate_credentials_configured() -> None:
    assert migrate_credentials(("configured", ("bi_user", ("password", "SECRET")))) == (
        "credentials",
        {"user": "bi_user", "secret": "SECRET"},
    )
