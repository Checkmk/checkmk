#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from typing import override

from cmk.maps.migration.legacy_maps import migrate_legacy_maps
from cmk.update_config.internal import ExpiryVersion, UpdateAction
from cmk.update_config.registry import update_action_registry


class MigrateLegacyMaps(UpdateAction):
    @override
    def __call__(self, logger: Logger, *, debug: bool) -> None:
        migrate_legacy_maps(logger)


update_action_registry.register(
    MigrateLegacyMaps(
        name="migrate_legacy_maps",
        title="Migrate OrbVis boards into Checkmk Maps",
        # After the pagetype actions; needs the users + pagetype store loadable.
        sort_index=130,
        expiry_version=ExpiryVersion.NEVER,
    )
)
