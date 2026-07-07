#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Sequence

import pytest

from cmk.utils.rulesets.definition import RuleGroup
from cmk.utils.rulesets.ruleset_matcher import RulesetName

from cmk.gui.valuespec import Dictionary
from cmk.gui.watolib.hosts_and_folders import folder_tree
from cmk.gui.watolib.rulesets import Rule, Ruleset, RulesetCollection
from cmk.gui.watolib.rulespec_groups import RulespecGroupMonitoringConfigurationVarious
from cmk.gui.watolib.rulespecs import HostRulespec

from cmk.update_config.plugins.actions.warn_obsolete_hivemanager_ng import (
    warn_obsolete_hivemanager_ng_rules,
)

LOGGER = logging.getLogger("test")

_LEGACY_RULE = {
    "url": "https://cloud.aerohive.com",
    "vhm_id": "102",
    "api_token": "token",
    "client_id": "clientID",
    "client_secret": ("cmk_postprocessed", "explicit_password", ("uuid", "secret")),
    "redirect_url": "https://redirect.com",
}


def _make_ruleset(name: RulesetName, rule_values: Sequence[object]) -> Ruleset:
    ruleset = Ruleset(
        name,
        {},
        rulespec=HostRulespec(
            name=name,
            group=RulespecGroupMonitoringConfigurationVarious,
            valuespec=lambda: Dictionary(elements=[], optional_keys=True),
        ),
    )
    folder = folder_tree().root_folder()
    for value in rule_values:
        rule = Rule.from_ruleset_defaults(folder, ruleset)
        rule.value = value
        ruleset.append_rule(folder, rule)
    return ruleset


@pytest.mark.usefixtures("request_context")
def test_warns_and_keeps_legacy_rules(caplog: pytest.LogCaptureFixture) -> None:
    name = RuleGroup.SpecialAgents("hivemanager_ng")
    all_rulesets = RulesetCollection({name: _make_ruleset(name, [_LEGACY_RULE])})

    with caplog.at_level(logging.WARNING):
        warn_obsolete_hivemanager_ng_rules(all_rulesets, LOGGER)

    assert "ExtremeCloud IQ" in caplog.text
    # The rule must not be touched - the configuration stays valid.
    assert [rule.value for _f, _i, rule in all_rulesets.get(name).get_rules()] == [_LEGACY_RULE]


@pytest.mark.usefixtures("request_context")
def test_no_warning_without_legacy_rules(caplog: pytest.LogCaptureFixture) -> None:
    name = RuleGroup.SpecialAgents("hivemanager_ng")
    all_rulesets = RulesetCollection({name: _make_ruleset(name, [])})

    with caplog.at_level(logging.WARNING):
        warn_obsolete_hivemanager_ng_rules(all_rulesets, LOGGER)

    assert not caplog.text


@pytest.mark.usefixtures("request_context")
def test_missing_ruleset(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        warn_obsolete_hivemanager_ng_rules(RulesetCollection({}), LOGGER)

    assert not caplog.text
