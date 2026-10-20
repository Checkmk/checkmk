#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

from logging import Logger

from cmk.schema_manager.managed_database import ManagedDatabase


def ensure_schema[ContextT](database: ManagedDatabase[ContextT], logger: Logger) -> None:
    """Apply the pending revisions of `database`'s chain, creating a missing database."""
    logger.debug("Applying pending schema revisions to %(name)s", {"name": database.name})
    with database.connect(create=True) as context:
        database.backend.apply_pending(context, database.chain, logger)
