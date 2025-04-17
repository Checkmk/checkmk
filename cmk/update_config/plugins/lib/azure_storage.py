#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Iterable
from typing import override

from cmk.update_config.plugins.lib.split_ruleset import MigrationDetail, RulesetSplitMigration


class AzureStorageMigration(RulesetSplitMigration):
    @override
    @property
    def old_ruleset_name(self) -> str:
        return "checkgroup_parameters:azure_storageaccounts"

    @override
    @property
    def ruleset_title(self) -> str:
        return "Azure Storage"

    @override
    @property
    def migration_rules(self) -> Iterable[MigrationDetail]:
        return [
            MigrationDetail(
                new_ruleset_name="checkgroup_parameters:azure_storageaccounts_flow",
                old_value_name="ingress_levels",
                new_value_name="ingress_levels",
                default_value=("no_levels", None),
            ),
            MigrationDetail(
                new_ruleset_name="checkgroup_parameters:azure_storageaccounts_flow",
                old_value_name="egress_levels",
                new_value_name="egress_levels",
                default_value=("no_levels", None),
            ),
            MigrationDetail(
                new_ruleset_name="checkgroup_parameters:azure_storageaccounts_usage",
                old_value_name="used_capacity_levels",
                new_value_name="used_capacity_levels",
                default_value=("no_levels", None),
            ),
            MigrationDetail(
                new_ruleset_name="checkgroup_parameters:azure_storageaccounts_performance",
                old_value_name="server_latency_levels",
                new_value_name="server_latency_levels",
                default_value=("no_levels", None),
            ),
            MigrationDetail(
                new_ruleset_name="checkgroup_parameters:azure_storageaccounts_performance",
                old_value_name="e2e_latency_levels",
                new_value_name="e2e_latency_levels",
                default_value=("no_levels", None),
            ),
            MigrationDetail(
                new_ruleset_name="checkgroup_parameters:azure_storageaccounts_flow",
                old_value_name="transactions_levels",
                new_value_name="transactions_levels",
                default_value=("no_levels", None),
            ),
            MigrationDetail(
                new_ruleset_name="checkgroup_parameters:azure_storageaccounts_performance",
                old_value_name="availability_levels",
                new_value_name="availability_levels",
                default_value=("no_levels", None),
            ),
        ]
