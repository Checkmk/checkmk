#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import sys
from collections.abc import Callable, Mapping

import pytest

from cmk.ccc.version import Edition
from cmk.gui.exceptions import MKUserError
from cmk.gui.valuespec import Dictionary, Float, Integer, Tuple
from cmk.gui.watolib.hosts_and_folders import FolderTree
from cmk.gui.watolib.rulesets import Rule, Ruleset, RulesetCollection
from cmk.gui.watolib.rulespec_groups import RulespecGroupMonitoringConfigurationVarious
from cmk.gui.watolib.rulespecs import HostRulespec, Rulespec
from cmk.ruleset_matcher.definition import RuleGroup
from cmk.ruleset_matcher.matcher import RulesetName
from cmk.update_config.plugins.actions import rulesets as rulesets_updater

_ARTIFICIAL_RULESPECS: Mapping[RulesetName, Rulespec] = {
    RuleGroup.CheckgroupParameters("ntp_time"): HostRulespec(
        name=RuleGroup.CheckgroupParameters("ntp_time"),
        group=RulespecGroupMonitoringConfigurationVarious,
        valuespec=lambda: Dictionary(
            elements=[("ntp_levels", Tuple(elements=[Integer(), Float(), Float()]))],
            optional_keys=True,
        ),
    ),
}


def _instantiate_ruleset(
    tree: FolderTree,
    ruleset_name: str,
    param_value: object,
    rulespec: Rulespec | None = None,
) -> Ruleset:
    ruleset = Ruleset(ruleset_name, rulespec=rulespec)
    folder = tree.root_folder()
    rule = Rule.from_ruleset(folder, ruleset, ruleset.rulespec.valuespec.default_value())
    rule.value = param_value
    ruleset.append_rule(folder, rule)
    assert ruleset.get_rules()
    return ruleset


@pytest.mark.parametrize(
    ["rulesets", "n_expected_warnings"],
    [
        pytest.param(
            lambda edition: {  # noqa: ARG005
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
            lambda edition: {
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
                    if edition is Edition.COMMUNITY
                    else {RuleGroup.ExtraServiceConf("_sla_config"): "i am skipped"}
                ),
            },
            0,
            id="valid configuration",
        ),
    ],
)
def test_validate_rule_values(
    caplog: pytest.LogCaptureFixture,
    tree: FolderTree,
    test_edition: Edition,
    rulesets: Callable[[Edition], Mapping[RulesetName, object]],
    n_expected_warnings: int,
) -> None:
    all_rulesets = RulesetCollection(
        {
            ruleset_name: _instantiate_ruleset(
                tree,
                ruleset_name,
                rule_value,
                _ARTIFICIAL_RULESPECS.get(ruleset_name),
            )
            for ruleset_name, rule_value in rulesets(test_edition).items()
        }
    )
    caplog.set_level(logging.INFO)
    rulesets_updater.validate_rule_values(logging.getLogger(), all_rulesets)
    assert len(caplog.messages) == n_expected_warnings


def test_validate_transformed_rule_values_reports_the_invalid_rule(tree: FolderTree) -> None:
    all_rulesets = RulesetCollection(
        {
            "logwatch_rules": _instantiate_ruleset(tree, "logwatch_rules", "not a dictionary"),
            RuleGroup.CheckgroupParameters("ntp_time"): _instantiate_ruleset(
                tree,
                RuleGroup.CheckgroupParameters("ntp_time"),
                {"ntp_levels": (10, 200.0, 500.0)},
                _ARTIFICIAL_RULESPECS[RuleGroup.CheckgroupParameters("ntp_time")],
            ),
        }
    )

    outcomes = list(rulesets_updater.validate_transformed_rule_values(all_rulesets))

    assert [
        (outcome.ruleset.name, outcome.index, type(outcome.problem)) for outcome in outcomes
    ] == [
        ("logwatch_rules", 0, MKUserError),
        (RuleGroup.CheckgroupParameters("ntp_time"), 0, type(None)),
    ]


def test_a_broken_ruleset_gets_a_crash_report_of_its_exception(
    tree: FolderTree, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The crash report is built from the exception being handled"""

    def _broken(_value: object, _varprefix: str) -> None:
        raise RuntimeError("the implementation is broken")

    name = RuleGroup.CheckgroupParameters("broken")
    all_rulesets = RulesetCollection(
        {
            name: _instantiate_ruleset(
                tree,
                name,
                {},
                HostRulespec(
                    name=name,
                    group=RulespecGroupMonitoringConfigurationVarious,
                    valuespec=lambda: Dictionary(elements=[], validate=_broken),
                ),
            )
        }
    )
    reported: list[BaseException | None] = []

    class _Report:
        def ident_to_text(self) -> str:
            reported.append(sys.exc_info()[1])
            return "the-crash-id"

    # the real factory writes the report into the site's crash directory
    monkeypatch.setattr(rulesets_updater, "create_gui_crash_report", _Report)

    rulesets_updater.validate_rule_values(logging.getLogger(), all_rulesets)

    assert [type(exc) for exc in reported] == [RuntimeError]
