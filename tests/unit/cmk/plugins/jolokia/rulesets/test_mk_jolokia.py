#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.jolokia.rulesets.mk_jolokia import rule_spec_mk_jolokia


def _migrate(value: object) -> object:
    migrate = rule_spec_mk_jolokia.parameter_form().migrate
    assert migrate is not None
    return migrate(value)


def test_migrate_login_with_stored_password() -> None:
    assert _migrate({"login": ("monitoring", ("store", "pw_id"), "basic")}) == {
        "deployment": "sync",
        "login": {
            "user": "monitoring",
            "password": ("cmk_postprocessed", "stored_password", ("pw_id", "")),
            "mode": "basic",
        },
    }


def test_migrate_login_with_explicit_password() -> None:
    match _migrate({"login": ("monitoring", ("password", "secret"), "digest")}):
        case {
            "deployment": "sync",
            "login": {
                "user": "monitoring",
                "password": ("cmk_postprocessed", "explicit_password", (str(), "secret")),
                "mode": "digest",
            },
        }:
            pass
        case other:
            raise AssertionError(other)
