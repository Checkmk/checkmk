#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Mapping

import pytest

from cmk.ccc.version import Edition, edition

from cmk.utils import paths
from cmk.utils.rulesets.definition import RuleGroup
from cmk.utils.rulesets.ruleset_matcher import RulesetName

from cmk.gui.watolib.hosts_and_folders import folder_tree
from cmk.gui.watolib.rulesets import Rule, Ruleset, RulesetCollection
from cmk.gui.watolib.rulespecs import Rulespec

from cmk.update_config.plugins.actions import rulesets as rulesets_updater


def _instantiate_ruleset(
    ruleset_name: str,
    param_value: object,
    rulespec: Rulespec | None = None,
) -> Ruleset:
    ruleset = Ruleset(ruleset_name, {}, rulespec=rulespec)
    folder = folder_tree().root_folder()
    rule = Rule.from_ruleset_defaults(folder, ruleset)
    rule.value = param_value
    ruleset.append_rule(folder, rule)
    assert ruleset.get_rules()
    return ruleset


@pytest.mark.parametrize(
    ["rulesets", "n_expected_warnings"],
    [
        pytest.param(
            {
                "logwatch_rules": {
                    "reclassify_patterns": [
                        ("C", "\\\\x\\\\y\\\\z", "some comment"),
                        ("W", "\\H", "invalid_regex"),
                    ]
                },
                RuleGroup.CheckgroupParameters("ntp_time"): {
                    "ntp_levels": (10, 200.0, 500.0),
                },
            },
            2,
            id="invalid configuration",
        ),
        pytest.param(
            {
                "logwatch_rules": {
                    "reclassify_patterns": [
                        ("C", "\\\\x\\\\y\\\\z", "some comment"),
                    ]
                },
                RuleGroup.CheckgroupParameters("ntp_time"): {
                    "ntp_levels": (10, 200.0, 500.0),
                },
                **(
                    {}
                    if edition(paths.omd_root) is Edition.CRE
                    else {RuleGroup.ExtraServiceConf("_sla_config"): "i am skipped"}
                ),
            },
            0,
            id="valid configuration",
        ),
    ],
)
@pytest.mark.usefixtures("request_context")
def test_validate_rule_values(
    caplog: pytest.LogCaptureFixture,
    rulesets: Mapping[RulesetName, object],
    n_expected_warnings: int,
) -> None:
    all_rulesets = RulesetCollection(
        {
            ruleset_name: _instantiate_ruleset(
                ruleset_name,
                rule_value,
            )
            for ruleset_name, rule_value in rulesets.items()
        }
    )
    caplog.set_level(logging.INFO)
    rulesets_updater.validate_rule_values(logging.getLogger(), all_rulesets)
    assert len(caplog.messages) == n_expected_warnings
