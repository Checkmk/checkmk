#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.quick_setup.v0_unstable.predefined import complete


def test_explicit_password_in_cascading_choice_is_replaced_by_stored_password() -> None:
    rule_params = {
        "auth": (
            "access_key",
            {"secret": ("cmk_postprocessed", "explicit_password", ("pw_id", "secret"))},
        )
    }

    converted = complete.convert_explicit_passwords_to_stored_passwords(rule_params, {"pw_id"})

    assert converted == {
        "auth": (
            "access_key",
            {"secret": ("cmk_postprocessed", "stored_password", ("pw_id", ""))},
        )
    }


def test_explicit_password_in_list_is_replaced_by_stored_password() -> None:
    rule_params = {
        "secrets": [
            "unrelated",
            ("cmk_postprocessed", "explicit_password", ("pw_id", "secret")),
        ]
    }

    converted = complete.convert_explicit_passwords_to_stored_passwords(rule_params, {"pw_id"})

    assert converted == {
        "secrets": [
            "unrelated",
            ("cmk_postprocessed", "stored_password", ("pw_id", "")),
        ]
    }


def test_explicit_password_with_unknown_id_is_kept() -> None:
    rule_params = {
        "auth": (
            "access_key",
            {"secret": ("cmk_postprocessed", "explicit_password", ("other_id", "secret"))},
        )
    }

    converted = complete.convert_explicit_passwords_to_stored_passwords(rule_params, {"pw_id"})

    assert converted == rule_params
