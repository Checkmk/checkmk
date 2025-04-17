#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Iterable
from typing import override

from cmk.update_config.plugins.lib.split_ruleset import MigrationDetail, RulesetSplitMigration


class AzureDatabaseMigration(RulesetSplitMigration):
    @override
    @property
    def ruleset_title(self) -> str:
        return "Azure Databases"

    @override
    @property
    def old_ruleset_name(self) -> str:
        return "checkgroup_parameters:azure_databases"

    @override
    @property
    def migration_rules(self) -> Iterable[MigrationDetail]:
        return [
            MigrationDetail(
                new_ruleset_name="checkgroup_parameters:azure_databases_storage",
                new_value_name="storage_percent",
                old_value_name="storage_percent_levels",
            ),
            MigrationDetail(
                new_ruleset_name="checkgroup_parameters:azure_databases_cpu",
                new_value_name="cpu_percent",
                old_value_name="cpu_percent_levels",
            ),
            MigrationDetail(
                new_ruleset_name="checkgroup_parameters:azure_databases_dtu",
                new_value_name="dtu_percent",
                old_value_name="dtu_percent_levels",
            ),
            MigrationDetail(
                new_ruleset_name="checkgroup_parameters:azure_databases_deadlock",
                new_value_name="deadlocks",
                old_value_name="deadlocks_levels",
            ),
        ]
