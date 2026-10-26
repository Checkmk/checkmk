#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.form_specs import get_visitor, RawDiskData, registration, VisitorOptions
from cmk.plugins.checkmk.rulesets.mk_inventory import migrate, rule_spec_mk_inventory
from cmk.rulesets.v1.form_specs import Dictionary

_REG = [r"Software\Microsoft\Windows\CurrentVersion\Uninstall"]


@pytest.mark.parametrize(
    "old, expected",
    [
        pytest.param(
            None,
            {
                "deployment": ("do_not_deploy", None),
                "interval": 14400.0,
                "reg_paths": ("default", None),
            },
            id="do_not_deploy",
        ),
        pytest.param(
            {},
            {
                "deployment": ("sync", None),
                "interval": 14400.0,
                "exe_paths": [],
                "reg_paths": ("custom", []),
            },
            id="old_empty",
        ),
        pytest.param(
            {"interval": 14400, "reg_paths": _REG},
            {
                "deployment": ("sync", None),
                "interval": 14400,
                "exe_paths": [],
                "reg_paths": ("custom", _REG),
            },
            id="old_partial",
        ),
        pytest.param(
            {"interval": 60, "exe_paths": ["C:\\tools"], "reg_paths": _REG},
            {
                "deployment": ("sync", None),
                "interval": 60,
                "exe_paths": ["C:\\tools"],
                "reg_paths": ("custom", _REG),
            },
            id="old_full",
        ),
        pytest.param(
            {"interval": 60, "exe_paths": [], "reg_paths": []},
            {
                "deployment": ("sync", None),
                "interval": 60,
                "exe_paths": [],
                "reg_paths": ("custom", []),
            },
            id="old_explicit_empty_lists",
        ),
        pytest.param(
            {"deployment": ("sync", None), "interval": 60.0},
            {"deployment": ("sync", None), "interval": 60.0},
            id="new",
        ),
    ],
)
def test_migrate(old: object, expected: dict[str, object]) -> None:
    assert migrate(old) == expected


@pytest.mark.parametrize(
    "value", [pytest.param("unexpected", id="str"), pytest.param([], id="list")]
)
def test_migrate_rejects_unknown_values(value: object) -> None:
    with pytest.raises(ValueError):
        migrate(value)


@pytest.fixture(name="rule_form")
def _rule_form() -> Dictionary:
    return rule_spec_mk_inventory.parameter_form()


@pytest.fixture
def _register_form_spec_visitors() -> None:
    registration.register()


def _validate_after_the_update(rule_form: Dictionary, rule: object) -> object:
    # The update migrates and stores the rule, then validates what it stored.
    updated = get_visitor(
        rule_form, VisitorOptions(migrate_values=True, mask_values=False)
    ).to_disk(RawDiskData(rule))
    return get_visitor(rule_form, VisitorOptions(migrate_values=False, mask_values=True)).validate(
        RawDiskData(updated)
    )


@pytest.mark.usefixtures("_register_form_spec_visitors")
def test_a_do_not_deploy_rule_validates_after_the_update(rule_form: Dictionary) -> None:
    """CMK-33871: a "do not deploy" rule of a previous release is valid after the update."""
    assert _validate_after_the_update(rule_form, None) == []
