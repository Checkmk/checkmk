#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest
from pytest_mock import MockerFixture

from cmk.utils.rulesets.conditions import HostOrServiceConditions

from cmk.gui.exceptions import MKUserError
from cmk.gui.watolib.hosts_and_folders import folder_tree
from cmk.gui.watolib.rulesets import (
    AllRulesets,
    Rule,
    RuleConditions,
    RuleOptions,
    Ruleset,
)

from cmk.update_config.plugins.pre_actions.rulesets import PreUpdateRulesets
from cmk.update_config.plugins.pre_actions.utils import ConflictMode


@pytest.mark.parametrize(
    ["host_condition", "expected"],
    [
        pytest.param(["ok_host", "ok.host", "okhost"], None, id="Valid conditions"),
        pytest.param(
            ["ok_host", "ok.host", "notohost*"],
            "invalid_host_condition",
            id="Invalid host condition",
        ),
        pytest.param(
            [{"$regex": "someregex.*"}, "ok.host", "okhost"], None, id="Valid conditions with regex"
        ),
        pytest.param(
            [{"$regex": "someregex.*"}, "ok.host", "notohost*"],
            "invalid_host_condition",
            id="Invalid host conditions with valid regex",
        ),
        pytest.param(
            {"$nor": ["ok_host", "ok.host", "okhost"]}, None, id="Valid negated host conditions"
        ),
        pytest.param(
            {"$nor": ["ok_host", "ok.host", "notohost*"]},
            "invalid_host_condition",
            id="Invalid negated host conditions",
        ),
        pytest.param(
            {"$nor": [{"$regex": "someregex.*"}, "ok.host", "okhost"]},
            None,
            id="Valid negated host conditions with valid regex",
        ),
        pytest.param(
            {"$nor": [{"$regex": "someregex.*"}, "ok.host", "notohost*"]},
            "invalid_host_condition",
            id="Invalid negated host conditions with valid regex",
        ),
    ],
)
def test_pre_rulesets(
    host_condition: HostOrServiceConditions, expected: str | None, mocker: MockerFixture
) -> None:
    root_folder = folder_tree().root_folder()
    ruleset_name = "automatic_host_removal"
    ruleset: Ruleset = Ruleset(ruleset_name, {})
    ruleset.append_rule(
        root_folder,
        Rule(
            id_="1",
            folder=root_folder,
            ruleset=ruleset,
            conditions=RuleConditions(
                host_folder=root_folder.path(),
                host_tags=None,
                host_label_groups=None,
                host_name=host_condition,
                service_description=None,
                service_label_groups=None,
            ),
            options=RuleOptions(
                disabled=None,
                description="",
                comment="",
                docu_url="",
            ),
            value=(
                "disabled",
                None,
            ),
        ),
    )
    mocker.patch(
        "cmk.update_config.plugins.pre_actions.rulesets.AllRulesets.load_all_rulesets",
        return_value=AllRulesets({ruleset_name: ruleset}),
    )
    if expected:
        with pytest.raises(MKUserError):
            assert _execute_pre_update_rulesets(mocker) == expected
    else:
        assert _execute_pre_update_rulesets(mocker) == expected


def _execute_pre_update_rulesets(mocker: MockerFixture) -> None | str:
    return PreUpdateRulesets(
        name="rulesets",
        title="Rulesets",
        sort_index=10,
    )(mocker.Mock(), ConflictMode.ABORT)
