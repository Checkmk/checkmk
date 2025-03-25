#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from logging import Logger
from typing import override

from cmk.gui.watolib.rulesets import AllRulesets

from cmk.update_config.plugins.lib.azure_databases import AzureDatabaseMigration
from cmk.update_config.registry import update_action_registry, UpdateAction


class MigrateAzureDatabases(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        migration = AzureDatabaseMigration(
            logger=logger, all_rulesets=AllRulesets.load_all_rulesets()
        )
        for error in migration:
            pass
        migration.all_rulesets.save()


update_action_registry.register(
    # Sort index is chosen such that this action is executed before "rulesets".
    # But this is only a weak requirement.
    MigrateAzureDatabases(name="azure-databases", title="Migrate Azure Databases", sort_index=29)
)
