#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging

import pytest

from cmk.gui.utils.script_helpers import gui_context
from cmk.gui.watolib.hosts_and_folders import Folder, FolderTree
from cmk.gui.watolib.rulesets import AllRulesets, Rule
from cmk.update_config.plugins.lib.azure_databases import AzureDatabaseMigration

logger = logging.getLogger("azure.databases")


def _migrate_and_assert(migration: AzureDatabaseMigration) -> None:
    error_count = 0
    for error in migration:
        error_count += 1
    assert error_count == 0


def test_migrate_no_ruleset() -> None:
    migration = AzureDatabaseMigration(logger, AllRulesets({}))
    _migrate_and_assert(migration)


def test_migrate_empty() -> None:
    with gui_context():
        all_rulesets = AllRulesets.load_all_rulesets()
        migration = AzureDatabaseMigration(logger, all_rulesets)
        old_ruleset = all_rulesets.get(migration.old_ruleset_name)
        for rule in old_ruleset.rules:
            old_ruleset.delete_rule(rule)

        _migrate_and_assert(migration)


@pytest.mark.parametrize(
    "value, new_ruleset_name",
    [
        pytest.param(
            {"cpu_percent_levels": (77.0, 99.0)},
            "checkgroup_parameters:azure_databases_cpu",
            id="CPU",
        ),
        pytest.param(
            {"dtu_percent_levels": (66.0, 88.0)},
            "checkgroup_parameters:azure_databases_dtu",
            id="DTU",
        ),
        pytest.param(
            {"deadlocks_levels": (77, 99)},
            "checkgroup_parameters:azure_databases_deadlock",
            id="Deadlocks",
        ),
        pytest.param(
            {"storage_percent_levels": (55.0, 77.0)},
            "checkgroup_parameters:azure_databases_storage",
            id="Storage",
        ),
    ],
)
def test_migrate(value: dict[str, tuple[float, float]], new_ruleset_name: str) -> None:
    with gui_context():
        all_rulesets = AllRulesets.load_all_rulesets()
        migration = AzureDatabaseMigration(logger, all_rulesets)
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
        assert len(new_rule.value) == len(value)
        assert list(new_rule.value.values()) == list(value.values())
