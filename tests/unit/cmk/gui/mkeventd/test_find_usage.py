#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

import cmk.ec.export as ec  # pylint: disable=cmk-module-layer-violation
from cmk.gui.mkeventd import _find_usage

_RULE_PACKS: Sequence[ec.ECRulePack] = [
    {
        "id": "default",
        "title": "Default rule pack",
        "disabled": False,
        "rules": [
            {
                "id": "test2",
                "contact_groups": {
                    "groups": ["my_contact_group"],
                    "notify": True,
                    "precedence": "host",
                },
            },
            {
                "id": "test4",
                "contact_groups": {"groups": ["all"], "notify": True, "precedence": "host"},
            },
            {
                "id": "test1",
                "contact_groups": {
                    "groups": ["my_contact_group"],
                    "notify": True,
                    "precedence": "host",
                },
            },
            {
                "id": "test",
                "contact_groups": {
                    "groups": ["my_contact_group"],
                    "notify": True,
                    "precedence": "host",
                },
            },
        ],
    }
]


@pytest.mark.usefixtures("request_context")
@pytest.mark.parametrize(
    "contact_group, rule_packs, expected_result",
    [
        pytest.param(
            "my_contact_group",
            _RULE_PACKS,
            [
                (
                    "Event console rule: test2",
                    "wato.py?edit=0&folder=&mode=mkeventd_edit_rule&rule_pack=default",
                ),
                (
                    "Event console rule: test1",
                    "wato.py?edit=2&folder=&mode=mkeventd_edit_rule&rule_pack=default",
                ),
                (
                    "Event console rule: test",
                    "wato.py?edit=3&folder=&mode=mkeventd_edit_rule&rule_pack=default",
                ),
            ],
            id="existing contact group, should match",
        ),
        pytest.param(
            "bielefeld",
            _RULE_PACKS,
            [],
            id="none existing contact group",
        ),
    ],
)
def test_find_usages_of_contact_group_in_ec_rules(
    contact_group: str,
    rule_packs: Sequence[ec.ECRulePack],
    expected_result: list[tuple[str, str]],
) -> None:
    assert (
        _find_usage.find_usages_of_contact_group_in_ec_rules(contact_group, {}, rule_packs)
        == expected_result
    )
