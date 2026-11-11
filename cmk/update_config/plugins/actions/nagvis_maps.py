#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from typing import override

from cmk.maps.migration.nagvis_maps import migrate_nagvis_maps
from cmk.update_config.internal import ExpiryVersion, UpdateAction
from cmk.update_config.registry import update_action_registry


class MigrateNagVisMaps(UpdateAction):
    @override
    def __call__(self, logger: Logger, *, debug: bool) -> None:
        migrate_nagvis_maps(logger)


update_action_registry.register(
    MigrateNagVisMaps(
        name="migrate_nagvis_maps",
        title="Migrate NagVis maps into Checkmk Maps",
        # After the OrbVis migration, whose boards keep their names.
        sort_index=131,
        expiry_version=ExpiryVersion.NEVER,
    )
)
