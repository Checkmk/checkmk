#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging

from cmk.gui.watolib.hosts_and_folders import FolderTree
from cmk.gui.watolib.rulesets import Rule, Ruleset, RulesetCollection
from cmk.gui.watolib.sample_config import CMK_INV_RULES
from cmk.update_config.plugins.actions.rulesets_add_inventory_rules import (
    add_cmk_inv_rules,
    CMK_INV_RULESET_NAME,
)


def _make_ruleset_collection(tree: FolderTree, rule_ids: list[str]) -> RulesetCollection:
    ruleset = Ruleset(CMK_INV_RULESET_NAME)
    folder = tree.root_folder()
    for rule_id in rule_ids:
        rule = Rule.from_ruleset(folder, ruleset, ruleset.rulespec.valuespec.default_value())
        rule.id = rule_id
        ruleset.append_rule(folder, rule)
    return RulesetCollection({ruleset.name: ruleset})


def test_ruleset_missing_does_nothing(tree: FolderTree) -> None:
    rulesets = RulesetCollection({})
    add_cmk_inv_rules(tree, logging.getLogger(), rulesets)
    assert CMK_INV_RULESET_NAME not in rulesets.get_rulesets()


def test_adds_all_rules_when_none_present(tree: FolderTree) -> None:
    rulesets = _make_ruleset_collection(tree, [])
    add_cmk_inv_rules(tree, logging.getLogger(), rulesets)
    assert rulesets.get_rulesets()[CMK_INV_RULESET_NAME].num_rules() == len(CMK_INV_RULES)
    for rule_config in CMK_INV_RULES:
        rulesets.get_rulesets()[CMK_INV_RULESET_NAME].get_rule_by_id(rule_config["id"])


def test_skips_rules_already_present(tree: FolderTree) -> None:
    all_ids = [r["id"] for r in CMK_INV_RULES]
    rulesets = _make_ruleset_collection(tree, all_ids)
    assert rulesets.get_rulesets()[CMK_INV_RULESET_NAME].num_rules() == len(CMK_INV_RULES)

    add_cmk_inv_rules(tree, logging.getLogger(), rulesets)

    assert rulesets.get_rulesets()[CMK_INV_RULESET_NAME].num_rules() == len(CMK_INV_RULES)


def test_adds_only_missing_rules(tree: FolderTree) -> None:
    first_id = CMK_INV_RULES[0]["id"]
    rulesets = _make_ruleset_collection(tree, [first_id])
    assert rulesets.get_rulesets()[CMK_INV_RULESET_NAME].num_rules() == 1

    add_cmk_inv_rules(tree, logging.getLogger(), rulesets)

    assert rulesets.get_rulesets()[CMK_INV_RULESET_NAME].num_rules() == len(CMK_INV_RULES)


def test_rules_are_prepended(tree: FolderTree) -> None:
    rulesets = _make_ruleset_collection(tree, ["some-unrelated-rule-id"])
    add_cmk_inv_rules(tree, logging.getLogger(), rulesets)

    all_rules = list(rulesets.get_rulesets()[CMK_INV_RULESET_NAME].get_rules())
    shipped_ids = {r["id"] for r in CMK_INV_RULES}
    # The shipped rules should come before the pre-existing unrelated rule
    shipped_positions = [i for i, (_, _idx, rule) in enumerate(all_rules) if rule.id in shipped_ids]
    unrelated_position = next(
        i for i, (_, _idx, rule) in enumerate(all_rules) if rule.id == "some-unrelated-rule-id"
    )
    assert all(pos < unrelated_position for pos in shipped_positions)


def test_idempotent(tree: FolderTree) -> None:
    rulesets = _make_ruleset_collection(tree, [])
    add_cmk_inv_rules(tree, logging.getLogger(), rulesets)
    count_after_first = rulesets.get_rulesets()[CMK_INV_RULESET_NAME].num_rules()

    add_cmk_inv_rules(tree, logging.getLogger(), rulesets)
    count_after_second = rulesets.get_rulesets()[CMK_INV_RULESET_NAME].num_rules()

    assert count_after_first == count_after_second
