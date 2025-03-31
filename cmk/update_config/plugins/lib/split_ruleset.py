#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Utilities for migrating rules of a ruleset that gets split up
"""

from abc import abstractmethod
from collections.abc import Generator, Iterable
from dataclasses import dataclass
from itertools import groupby
from logging import Logger
from typing import Any

from cmk.gui.watolib.rulesets import AllRulesets, Rule, Ruleset


@dataclass(frozen=True)
class MigrationDetail:
    new_ruleset_name: str
    old_value_name: str
    new_value_name: str
    default_value: Any = None


@dataclass(frozen=True)
class MigrationError:
    exception: Exception
    message: str


class RulesetSplitMigration:
    @property
    @abstractmethod
    def ruleset_title(self) -> str: ...

    @property
    @abstractmethod
    def old_ruleset_name(self) -> str: ...

    @property
    @abstractmethod
    def migration_rules(self) -> Iterable[MigrationDetail]: ...

    def __init__(self, logger: Logger, all_rulesets: AllRulesets) -> None:
        self.all_rulesets = all_rulesets
        self.logger = logger

    def _create_ruleset(
        self,
        old_ruleset: Ruleset,
        new_ruleset_name: str,
        migration_details: Iterable[MigrationDetail],
    ) -> None:
        try:
            new_ruleset = self.all_rulesets.get(new_ruleset_name)
            self.logger.debug("Adding migrated rules to existing ruleset %s", new_ruleset.name)
        except KeyError:
            new_ruleset = Ruleset(
                name=new_ruleset_name,
                tag_to_group_map=old_ruleset.tag_to_group_map,
            )
            self.all_rulesets.set(new_ruleset_name, new_ruleset)
            self.logger.debug("Created new ruleset %s", new_ruleset.name)

        self._clone_rules(old_ruleset, new_ruleset, migration_details)

    def _clone_rules(
        self,
        old_ruleset: Ruleset,
        new_ruleset: Ruleset,
        migration_details: Iterable[MigrationDetail],
    ) -> None:
        for name, rules in old_ruleset.rules.items():
            for idx, rule in enumerate(rules):
                value = {}
                for migration_detail in migration_details:
                    if (
                        migration_detail.old_value_name not in rule.value
                        and migration_detail.default_value is None
                    ):
                        self.logger.debug(
                            "No value for rule %s. Skipping", migration_detail.old_value_name
                        )
                        continue

                    self.logger.debug(
                        "Adding value %s to rule %s",
                        migration_detail.old_value_name,
                        new_ruleset.name,
                    )
                    value[migration_detail.new_value_name] = rule.value.get(
                        migration_detail.old_value_name, migration_detail.default_value
                    )

                new_ruleset.append_rule(
                    folder=rule.folder,
                    rule=Rule(
                        id_=f"migrated-{idx}-{rule.id}",
                        folder=rule.folder,
                        ruleset=new_ruleset,
                        conditions=rule.conditions,
                        options=rule.rule_options,
                        value=value,
                    ),
                )

    def __iter__(self) -> Generator[MigrationError, None, None]:
        try:
            old_ruleset = self.all_rulesets.get(self.old_ruleset_name)
        except KeyError:
            self.logger.debug(f"No {self.ruleset_title} ruleset to migrate.")
            return None

        if old_ruleset.is_empty():
            self.logger.debug(f"{self.ruleset_title} ruleset has no rules.")
            return None

        sort_func = lambda item: item.new_ruleset_name

        for new_ruleset_name, migration_group in groupby(
            sorted(self.migration_rules, key=sort_func), key=sort_func
        ):
            _migration_group: list[MigrationDetail] = list(migration_group)
            self.logger.debug(
                "Migrating %s rule values %s to new ruleset",
                self.ruleset_title,
                [detail.old_value_name for detail in _migration_group],
            )
            try:
                self._create_ruleset(
                    old_ruleset=old_ruleset,
                    new_ruleset_name=new_ruleset_name,
                    migration_details=_migration_group,
                )
            except Exception as exc:
                yield MigrationError(
                    exception=exc,
                    message=f"Failed to create new ruleset {new_ruleset_name} for {self.old_ruleset_name.split(':', 1)[-1]} ruleset migration",
                )

        try:
            self.all_rulesets.delete(old_ruleset.name)
        except Exception as exc:
            yield MigrationError(
                exception=exc,
                message=f"Failed to delete old {self.old_ruleset_name.split(':', 1)[-1]} ruleset",
            )
