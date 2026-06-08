#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Tests for the legacy `inventory_*_rules` -> `discovery_parameters:<name>` migration."""

from logging import getLogger

import pytest

from cmk.gui.valuespec import Dictionary, TextInput
from cmk.gui.watolib.hosts_and_folders import folder_tree
from cmk.gui.watolib.rulesets import Ruleset, RulesetCollection
from cmk.gui.watolib.rulespec_groups import RulespecGroupMonitoringConfigurationVarious
from cmk.gui.watolib.rulespecs import HostRulespec, Rulespec, rulespec_registry
from cmk.update_config.plugins.lib import rulesets as rulesets_updater
from cmk.utils.rulesets.definition import RuleGroup
from cmk.utils.rulesets.ruleset_matcher import RuleSpec


@pytest.fixture(name="legacy_name")
def fixture_legacy_name() -> str:
    return "inventory_df_rules"


@pytest.fixture(name="new_name")
def fixture_new_name(legacy_name: str) -> str:
    return RuleGroup.DiscoveryParameters(legacy_name)


@pytest.fixture(name="discovery_rulespec")
def fixture_discovery_rulespec(new_name: str) -> Rulespec:
    return HostRulespec(
        group=RulespecGroupMonitoringConfigurationVarious,
        name=new_name,
        valuespec=lambda: Dictionary(elements=[("mount", TextInput())], optional_keys=True),
        match_type="dict",
    )


@pytest.fixture(name="registered_discovery_rulespec")
def fixture_registered_discovery_rulespec(discovery_rulespec: Rulespec) -> object:
    rulespec_registry.register(discovery_rulespec)
    try:
        yield discovery_rulespec
    finally:
        rulespec_registry.unregister(discovery_rulespec.name)


def _unknown_rule_spec(value: object) -> RuleSpec[object]:
    return RuleSpec(
        id="rule-id-1",
        condition={},
        value=value,
    )


@pytest.mark.usefixtures("request_context", "registered_discovery_rulespec")
def test_discovery_parameter_renames_picks_up_registered_rulespec(
    legacy_name: str, new_name: str
) -> None:
    renames = rulesets_updater._discovery_parameter_renames()
    assert renames[legacy_name] == new_name


@pytest.mark.usefixtures("request_context", "registered_discovery_rulespec")
def test_discovery_parameter_renames_skips_unrelated_rulespecs() -> None:
    renames = rulesets_updater._discovery_parameter_renames()
    # All resulting keys must come from rulespecs with the discovery_parameters: prefix
    for old, new in renames.items():
        assert new.startswith(RuleGroup.DiscoveryParameters(""))
        assert new.split(":", 1)[1] == old


@pytest.mark.usefixtures("request_context")
def test_transform_migrates_unknown_inventory_ruleset_to_discovery_parameters(
    discovery_rulespec: Rulespec, legacy_name: str, new_name: str
) -> None:
    all_rulesets = RulesetCollection({new_name: Ruleset(new_name, rulespec=discovery_rulespec)})
    folder = folder_tree().root_folder()
    all_rulesets._unknown_rulesets[folder.path()] = {
        legacy_name: [_unknown_rule_spec({"mount": "/var"})],
    }

    rulesets_updater.transform_replaced_wato_rulesets(
        getLogger(), all_rulesets, {legacy_name: new_name}
    )

    assert legacy_name not in all_rulesets.get_unknown_rulesets().get(folder.path(), {})
    rules = all_rulesets.get(new_name).get_rules()
    assert len(rules) == 1
    assert rules[0][2].value == {"mount": "/var"}


@pytest.mark.usefixtures("request_context")
def test_transform_preserves_unrelated_unknown_rulesets(
    discovery_rulespec: Rulespec, legacy_name: str, new_name: str
) -> None:
    all_rulesets = RulesetCollection({new_name: Ruleset(new_name, rulespec=discovery_rulespec)})
    folder = folder_tree().root_folder()
    all_rulesets._unknown_rulesets[folder.path()] = {
        legacy_name: [_unknown_rule_spec({"mount": "/var"})],
        "some_local_plugin_rules": [_unknown_rule_spec({"foo": 42})],
    }

    rulesets_updater.transform_replaced_wato_rulesets(
        getLogger(), all_rulesets, {legacy_name: new_name}
    )

    surviving = all_rulesets.get_unknown_rulesets()[folder.path()]
    assert "some_local_plugin_rules" in surviving
    assert surviving["some_local_plugin_rules"][0]["value"] == {"foo": 42}


@pytest.mark.usefixtures("request_context")
def test_transform_is_idempotent_on_already_migrated_configs(
    discovery_rulespec: Rulespec, legacy_name: str, new_name: str
) -> None:
    all_rulesets = RulesetCollection({new_name: Ruleset(new_name, rulespec=discovery_rulespec)})
    folder = folder_tree().root_folder()
    all_rulesets._unknown_rulesets[folder.path()] = {
        legacy_name: [_unknown_rule_spec({"mount": "/var"})],
    }

    rulesets_updater.transform_replaced_wato_rulesets(
        getLogger(), all_rulesets, {legacy_name: new_name}
    )
    rulesets_updater.transform_replaced_wato_rulesets(
        getLogger(), all_rulesets, {legacy_name: new_name}
    )

    rules = all_rulesets.get(new_name).get_rules()
    assert len(rules) == 1
