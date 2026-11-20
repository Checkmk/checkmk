#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Mapping

import pytest

from cmk.ccc.version import Edition, edition
from cmk.gui.valuespec import Dictionary
from cmk.gui.watolib.hosts_and_folders import folder_tree
from cmk.gui.watolib.rulesets import Rule, Ruleset, RulesetCollection
from cmk.gui.watolib.rulespec_groups import RulespecGroupMonitoringConfigurationVarious
from cmk.gui.watolib.rulespecs import FormSpecDefinition, HostRulespec, Rulespec
from cmk.rulesets.v1 import form_specs
from cmk.update_config.plugins.actions import rulesets as rulesets_updater
from cmk.utils import paths
from cmk.utils.rulesets.definition import RuleGroup
from cmk.utils.rulesets.ruleset_matcher import RulesetName

_FORM_SPEC_RULESET = RuleGroup.CheckgroupParameters("form_spec_only")

_FORM_SPEC_RULESPEC = HostRulespec(
    name=_FORM_SPEC_RULESET,
    group=RulespecGroupMonitoringConfigurationVarious,
    valuespec=lambda: Dictionary(elements=[]),
    form_spec_definition=FormSpecDefinition(
        lambda: form_specs.Dictionary(
            elements={
                "name": form_specs.DictElement(
                    parameter_form=form_specs.String(
                        custom_validate=(form_specs.validators.LengthInRange(min_value=1),),
                    ),
                ),
            },
        ),
        None,
    ),
)


def _instantiate_ruleset(
    ruleset_name: str,
    param_value: object,
    rulespec: Rulespec | None = None,
) -> Ruleset:
    ruleset = Ruleset(ruleset_name, rulespec=rulespec)
    folder = folder_tree().root_folder()
    rule = Rule.from_ruleset(folder, ruleset, ruleset.rulespec.valuespec.default_value())
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
                    if edition(paths.omd_root) is Edition.COMMUNITY
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


_INVALID = "Invalid rule configuration detected"
_BROKEN = "Exception in ruleset implementation detected"


@pytest.mark.parametrize(
    ["ruleset_name", "rule_value", "rulespec", "expected_warning"],
    [
        pytest.param(
            "logwatch_rules",
            {"reclassify_patterns": [("W", "\\H", "invalid_regex")]},
            None,
            _INVALID,
            id="valuespec rejects the value",
        ),
        pytest.param(
            "logwatch_rules",
            "not a dictionary",
            None,
            _BROKEN,
            id="valuespec cannot parse the value",
        ),
        pytest.param(
            _FORM_SPEC_RULESET,
            {"name": ""},
            _FORM_SPEC_RULESPEC,
            _INVALID,
            id="form spec rejects the value",
        ),
        pytest.param(
            _FORM_SPEC_RULESET,
            {"name": 5},
            _FORM_SPEC_RULESPEC,
            _BROKEN,
            id="form spec cannot parse the value",
        ),
    ],
)
@pytest.mark.usefixtures("request_context")
def test_validate_rule_values_tells_unparsable_from_rejected_values(
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
    ruleset_name: RulesetName,
    rule_value: object,
    rulespec: Rulespec | None,
    expected_warning: str,
) -> None:
    crash_reports: list[_FakeCrashReport] = []

    def _create_crash_report() -> _FakeCrashReport:
        crash_reports.append(report := _FakeCrashReport())
        return report

    monkeypatch.setattr(rulesets_updater, "create_gui_crash_report", _create_crash_report)
    all_rulesets = RulesetCollection(
        {ruleset_name: _instantiate_ruleset(ruleset_name, rule_value, rulespec)}
    )
    rulesets_updater.validate_rule_values(logging.getLogger(), all_rulesets)
    assert [
        warning for m in caplog.messages for warning in (_INVALID, _BROKEN) if warning in m
    ] == [expected_warning]
    assert len(crash_reports) == (1 if expected_warning == _BROKEN else 0)


class _FakeCrashReport:
    def ident_to_text(self) -> str:
        return "fake-crash-id"
