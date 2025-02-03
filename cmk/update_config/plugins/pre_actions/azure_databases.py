#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from logging import Logger

from cmk.gui.exceptions import MKUserError
from cmk.gui.watolib.rulesets import AllRulesets

from cmk.update_config.plugins.lib.azure_databases import AzureDatabaseMigration
from cmk.update_config.plugins.pre_actions.utils import (
    ConflictMode,
    continue_per_users_choice,
)
from cmk.update_config.registry import pre_update_action_registry, PreUpdateAction


class MigrateAzureDatabases(PreUpdateAction):
    @staticmethod
    def _continue_on_exception(conflict_mode: ConflictMode) -> bool:
        match conflict_mode:
            case ConflictMode.FORCE | ConflictMode.INSTALL:
                return True
            case ConflictMode.ABORT | ConflictMode.KEEP_OLD:
                return False
            case ConflictMode.ASK:
                return continue_per_users_choice(
                    "You can abort the update process (A) and try to fix "
                    "the incompatibilities or try to continue the update (c).\n"
                    "Abort update? [A/c]\n"
                ).is_not_abort()

    def __call__(self, logger: Logger, conflict_mode: ConflictMode) -> None:
        for error in AzureDatabaseMigration(
            logger=logger, all_rulesets=AllRulesets.load_all_rulesets()
        ):
            logger.error(
                "The azure_databases ruleset migration raised a %s exception: %s",
                error.exception,
                error.message,
            )
            if self._continue_on_exception(conflict_mode=conflict_mode):
                continue
            raise MKUserError(None, "Failed to migrate azure_databases")


pre_update_action_registry.register(
    # Sort index is chosen such that this action is executed before "rulesets"
    MigrateAzureDatabases(name="azure-databases", title="Migrate Azure Databases", sort_index=29)
)
