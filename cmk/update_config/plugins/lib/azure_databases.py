#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Generator
from dataclasses import dataclass
from logging import Logger

from cmk.gui.watolib.rulesets import AllRulesets, Rule, Ruleset


@dataclass(frozen=True)
class MigrationDetail:
    new_ruleset_name: str
    old_value_name: str
    new_value_name: str


@dataclass(frozen=True)
class MigrationError:
    exception: Exception
    message: str


class AzureDatabaseMigration:
    old_ruleset_name = "checkgroup_parameters:azure_databases"
    rule_mapping = {
        "storage_percent_levels": MigrationDetail(
            new_ruleset_name="checkgroup_parameters:azure_databases_storage",
            new_value_name="storage_percent",
            old_value_name="storage_percent_levels",
        ),
        "cpu_percent_levels": MigrationDetail(
            new_ruleset_name="checkgroup_parameters:azure_databases_cpu",
            new_value_name="cpu_percent",
            old_value_name="cpu_percent_levels",
        ),
        "dtu_percent_levels": MigrationDetail(
            new_ruleset_name="checkgroup_parameters:azure_databases_dtu",
            new_value_name="dtu_percent",
            old_value_name="dtu_percent_levels",
        ),
        "deadlocks_levels": MigrationDetail(
            new_ruleset_name="checkgroup_parameters:azure_databases_deadlock",
            new_value_name="deadlocks",
            old_value_name="deadlocks_levels",
        ),
    }

    def __init__(self, logger: Logger, all_rulesets: AllRulesets) -> None:
        self.all_rulesets = all_rulesets
        self.logger = logger

    def _create_ruleset(self, old_ruleset: Ruleset, migration_detail: MigrationDetail) -> None:
        try:
            new_ruleset = self.all_rulesets.get(migration_detail.new_ruleset_name)
            self.logger.debug("Adding migrated rules to existing ruleset %s", new_ruleset.name)
        except KeyError:
            new_ruleset = Ruleset(
                name=migration_detail.new_ruleset_name,
                tag_to_group_map=old_ruleset.tag_to_group_map,
            )
            self.all_rulesets.set(migration_detail.new_ruleset_name, new_ruleset)
            self.logger.debug("Created new ruleset %s", new_ruleset.name)

        self._clone_rules(old_ruleset, new_ruleset, migration_detail)

    def _clone_rules(
        self, old_ruleset: Ruleset, new_ruleset: Ruleset, migration_detail: MigrationDetail
    ) -> None:
        for name, rules in old_ruleset.rules.items():
            for idx, rule in enumerate(rules):
                if migration_detail.old_value_name not in rule.value:
                    self.logger.debug("No value for rule %s. Skipping", name)
                    continue

                self.logger.debug("Adding rule %s to ruleset %s", name, new_ruleset.name)
                new_ruleset.append_rule(
                    folder=rule.folder,
                    rule=Rule(
                        id_=f"migrated-{idx}-{rule.id}",
                        folder=rule.folder,
                        ruleset=new_ruleset,
                        conditions=rule.conditions,
                        options=rule.rule_options,
                        value={
                            migration_detail.new_value_name: rule.value[
                                migration_detail.old_value_name
                            ]
                        },
                    ),
                )

    def __iter__(self) -> Generator[MigrationError, None, None]:
        try:
            old_ruleset = self.all_rulesets.get(self.old_ruleset_name)
        except KeyError:
            self.logger.info("No Azure Databases ruleset to migrate.")
            return None

        if old_ruleset.is_empty():
            self.logger.info("Azure Databases ruleset has no rules.")
            return None

        for rule_param, migration_detail in self.rule_mapping.items():
            self.logger.debug("Migrating Azure Databases rule value %s to new ruleset", rule_param)
            try:
                self._create_ruleset(old_ruleset=old_ruleset, migration_detail=migration_detail)
            except Exception as exc:
                yield MigrationError(
                    exception=exc,
                    message=f"Failed to create new ruleset {migration_detail.new_ruleset_name} for azure_databases ruleset migration",
                )

        try:
            self.all_rulesets.delete(old_ruleset.name)
        except Exception as exc:
            yield MigrationError(
                exception=exc, message="Failed to delete old azure_databases ruleset"
            )
