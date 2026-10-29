#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable
from logging import Logger

from cmk.schema_manager.managed_database import ManagedDatabase


def ensure_schema[ContextT](database: ManagedDatabase[ContextT], logger: Logger) -> None:
    """Apply the pending revisions of `database`'s chain, creating a missing database."""
    logger.debug("Applying pending schema revisions to %(name)s", {"name": database.name})
    with database.connect(create=True) as context:
        database.backend.apply_pending(context, database.chain, logger)


def ensure_schemas_on_update[ContextT](
    databases: Iterable[ManagedDatabase[ContextT]], logger: Logger
) -> None:
    """Like `ensure_schema`, but skips a missing database that did not opt
    into "create": sites older than the database never ran its post-create
    hook, and its consumer creates it.

    Tries every database, so one run reports all broken ones, and raises
    afterwards.
    """
    failed = []
    for database in databases:
        if not database.exists() and "create" not in database.omd_lifecycle:
            continue
        try:
            ensure_schema(database, logger)
        except Exception as e:
            logger.error(  # noqa: TRY400
                "Failed to apply schema revisions to %(name)s: %(error)s",
                {"name": database.name, "error": e},
            )
            failed.append(database.name)
    if failed:
        raise RuntimeError(f"Failed to apply schema revisions to: {', '.join(failed)}")
