#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from logging import Logger
from typing import override

from cmk.gui.config import active_config
from cmk.gui.watolib.rulesets import AllRulesets
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.plugins.lib.azure_storage import AzureStorageMigration
from cmk.update_config.registry import update_action_registry, UpdateAction


class MigrateAzureStorage(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        migration = AzureStorageMigration(
            logger=logger, all_rulesets=AllRulesets.load_all_rulesets()
        )
        for error in migration:
            pass
        migration.all_rulesets.save(
            pprint_value=active_config.wato_pprint_config, debug=active_config.debug
        )


update_action_registry.register(
    # Sort index is chosen such that this action is executed before "rulesets".
    # But this is only a weak requirement.
    MigrateAzureStorage(
        name="azure-storage",
        title="Migrate Azure Storage",
        sort_index=29,
        expiry_version=ExpiryVersion.CMK_300,
    )
)
