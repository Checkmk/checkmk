#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ec.export import ECRulePack  # pylint: disable=cmk-module-layer-violation

from cmk.gui.mkeventd import _find_usage


def _rule_packs() -> list[ECRulePack]:
    return [
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
                    "contact_groups": {
                        "groups": ["all"],
                        "notify": True,
                        "precedence": "host",
                    },
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
            _rule_packs,
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
            _rule_packs,
            [],
            id="none existing contact group",
        ),
    ],
)
def test_find_usages_of_contact_group_in_ec_rules(
    monkeypatch: pytest.MonkeyPatch,
    contact_group: str,
    rule_packs: list[ECRulePack],
    expected_result: list[tuple[str, str]],
) -> None:
    monkeypatch.setattr(_find_usage, "load_rule_packs", rule_packs)
    assert (
        _find_usage.find_usages_of_contact_group_in_ec_rules(contact_group, {}) == expected_result
    )
