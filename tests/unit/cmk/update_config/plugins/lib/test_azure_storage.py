#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging

import pytest

from cmk.gui.utils.script_helpers import gui_context
from cmk.gui.watolib.hosts_and_folders import Folder, FolderTree
from cmk.gui.watolib.rulesets import AllRulesets, Rule

from cmk.update_config.plugins.lib.azure_storage import AzureStorageMigration

logger = logging.getLogger("azure.storage")


def _migrate_and_assert(migration: AzureStorageMigration) -> None:
    error_count = 0
    for error in migration:
        error_count += 1
    assert error_count == 0


def test_migrate_no_ruleset() -> None:
    migration = AzureStorageMigration(logger, AllRulesets({}))
    _migrate_and_assert(migration)


def test_migrate_empty() -> None:
    with gui_context():
        all_rulesets = AllRulesets.load_all_rulesets()
        migration = AzureStorageMigration(logger, all_rulesets)
        old_ruleset = all_rulesets.get(migration.old_ruleset_name)
        for rule in old_ruleset.rules:
            old_ruleset.delete_rule(rule)

        _migrate_and_assert(migration)


@pytest.mark.parametrize(
    ["value", "new_ruleset_name", "expected_value"],
    [
        pytest.param(
            {"used_capacity_levels": (10 * 1024**3, 12 * 1024**3)},
            "checkgroup_parameters:azure_storageaccounts_usage",
            {"used_capacity_levels": (10 * 1024**3, 12 * 1024**3)},
            id="Capacity usage",
        ),
        pytest.param(
            {"ingress_levels": (5 * 1024**2, 10 * 1024**2)},
            "checkgroup_parameters:azure_storageaccounts_flow",
            {
                "transactions_levels": ("no_levels", None),
                "ingress_levels": (5 * 1024**2, 10 * 1024**2),
                "egress_levels": ("no_levels", None),
            },
            id="Ingress",
        ),
        pytest.param(
            {"server_latency_levels": (700, 900)},
            "checkgroup_parameters:azure_storageaccounts_performance",
            {
                "server_latency_levels": (700, 900),
                "e2e_latency_levels": ("no_levels", None),
                "availability_levels": ("no_levels", None),
            },
            id="Server Latency",
        ),
    ],
)
def test_migrate(
    value: dict[str, tuple[float, float]], new_ruleset_name: str, expected_value: dict[str, object]
) -> None:
    with gui_context():
        all_rulesets = AllRulesets.load_all_rulesets()
        migration = AzureStorageMigration(logger, all_rulesets)
        old_ruleset = all_rulesets.get(migration.old_ruleset_name)
        for rule in old_ruleset.rules:
            old_ruleset.delete_rule(rule)

        folder = Folder.load(tree=FolderTree(), name="Main", parent_folder=None)
        old_rule = Rule.from_ruleset_defaults(folder, old_ruleset)
        old_rule.value = value
        old_ruleset.append_rule(folder, old_rule)

        _migrate_and_assert(migration)

        with pytest.raises(KeyError):
            migration.all_rulesets.get(migration.old_ruleset_name)

        new_ruleset = all_rulesets.get(new_ruleset_name)
        assert not new_ruleset.is_empty()

        new_rule = new_ruleset.get_rule_by_id(f"migrated-0-{old_rule.id}")
        assert new_rule.value == expected_value
