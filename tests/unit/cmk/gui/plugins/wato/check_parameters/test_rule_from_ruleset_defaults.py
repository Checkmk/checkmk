#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

import pytest

from cmk.gui.plugins.wato.check_parameters.local import _parameter_valuespec_local
from cmk.gui.plugins.wato.check_parameters.ps import _valuespec_inventory_processes_rules
from cmk.gui.watolib import rulesets
from cmk.gui.watolib import rulesets as gui_rulesets_module
from cmk.gui.watolib.hosts_and_folders import folder_tree
from cmk.gui.watolib.rulesets import RuleOptions, RuleValue
from cmk.utils.rulesets.definition import RuleGroup
from cmk.utils.rulesets.ruleset_matcher import RulesetName


def _ruleset(ruleset_name: RulesetName) -> rulesets.Ruleset:
    return rulesets.Ruleset(ruleset_name)


GEN_ID_COUNT = {"c": 0}


@pytest.fixture(autouse=True)
def fixture_gen_id(monkeypatch: pytest.MonkeyPatch, request_context: None) -> None:
    GEN_ID_COUNT["c"] = 0

    def _gen_id():
        GEN_ID_COUNT["c"] += 1
        return str(GEN_ID_COUNT["c"])

    monkeypatch.setattr(gui_rulesets_module, "gen_id", _gen_id)


@pytest.mark.parametrize(
    "ruleset_name,default_value,is_binary",
    [
        # non-binary host ruleset
        (
            "inventory_processes_rules",
            _valuespec_inventory_processes_rules().default_value(),
            False,
        ),
        # binary host ruleset
        ("only_hosts", True, True),
        # non-binary service ruleset
        (
            RuleGroup.CheckgroupParameters("local"),
            _parameter_valuespec_local().default_value(),
            False,
        ),
        # binary service ruleset
        ("clustered_services", True, True),
    ],
)
def test_rule_from_ruleset_defaults(
    ruleset_name: str, default_value: RuleValue, is_binary: bool
) -> None:
    ruleset = _ruleset(ruleset_name)
    rule = rulesets.Rule.from_ruleset(
        folder_tree().root_folder(), ruleset, ruleset.rulespec.valuespec.default_value()
    )
    assert isinstance(rule.conditions, rulesets.RuleConditions)
    assert rule.rule_options == RuleOptions(
        disabled=False,
        description="",
        comment="",
        docu_url="",
        predefined_condition_id=None,
    )
    assert rule.value == default_value
    assert rule.ruleset.rulespec.is_binary_ruleset == is_binary
