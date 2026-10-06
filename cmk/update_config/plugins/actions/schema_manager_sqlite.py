#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Apply pending SQLite schema-manager revisions on `omd update`."""

from logging import Logger
from typing import override

from cmk.schema_manager.backend.sqlite import ensure_sqlite_up_to_date
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.registry import update_action_registry, UpdateAction


class MigrateSqliteSchemas(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        ensure_sqlite_up_to_date(logger)


update_action_registry.register(
    MigrateSqliteSchemas(
        name="schema_manager_sqlite",
        title="Apply pending SQLite schema-manager revisions",
        sort_index=5,
        expiry_version=ExpiryVersion.NEVER,
    )
)
