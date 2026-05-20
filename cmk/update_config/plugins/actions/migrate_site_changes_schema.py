#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Rewrite stored ``SiteChanges`` records to the new on-disk schema.

The ``add_change`` write path used to persist three flags that the new
``PendingChanges`` recorder no longer writes:

  * ``need_sync`` (bool, resolved at write time) -> ``force_sync``
  * ``need_restart`` (bool, resolved at write time) -> ``force_restart``
  * ``has_been_activated`` (bool, derived at write time) -> dropped
    (recomputed by readers from the change and the current site config)

This update action rewrites legacy records in place so that the application
code can uniformly rely on the new schema.
"""

from logging import Logger
from typing import Any, cast, override

from cmk.ccc.site import SiteId
from cmk.gui.watolib.paths import wato_var_dir
from cmk.gui.watolib.site_changes import SiteChanges
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.registry import update_action_registry, UpdateAction

# Match the file name pattern used by SiteChanges:
#   wato_var_dir() / "replication_changes_{site_id}.mk"
_SITE_CHANGES_PREFIX = "replication_changes_"
_SITE_CHANGES_SUFFIX = ".mk"


def _migrate_record(record: dict[str, Any]) -> bool:
    changed = False

    if "need_sync" in record:
        # Treat the stored resolved bool as the caller's explicit override
        # in the new schema. We cannot recover whether the original caller
        # passed None and let the writer derive the value, so we preserve
        # the legacy interpretation verbatim.
        record["force_sync"] = record.pop("need_sync")
        changed = True

    if "need_restart" in record:
        record["force_restart"] = record.pop("need_restart")
        changed = True

    if "force_apache_reload" not in record:
        # Old records never wrote this flag. Default to False - the
        # historical add_change() defaulted need_apache_reload to False too.
        record["force_apache_reload"] = False
        changed = True

    if "has_been_activated" in record:
        # Recomputed at read time from (change, current site config).
        del record["has_been_activated"]
        changed = True

    return changed


class MigrateSiteChangesSchema(UpdateAction):
    """Rewrite per-site change journals into the new on-disk schema."""

    @override
    def __call__(self, logger: Logger) -> None:
        site_changes_dir = wato_var_dir()
        if not site_changes_dir.exists():
            return

        for path in sorted(site_changes_dir.glob(f"{_SITE_CHANGES_PREFIX}*{_SITE_CHANGES_SUFFIX}")):
            if not path.is_file():
                continue

            site_id = SiteId(path.name[len(_SITE_CHANGES_PREFIX) : -len(_SITE_CHANGES_SUFFIX)])
            store = SiteChanges(site_id)
            if not store.exists():
                continue

            with store.mutable_view() as records:
                migrated = sum(
                    1 for record in records if _migrate_record(cast("dict[str, Any]", record))
                )

            if migrated:
                logger.info(
                    "Migrated %d pending change(s) for site %r to the new schema.",
                    migrated,
                    site_id,
                )


update_action_registry.register(
    MigrateSiteChangesSchema(
        name="migrate_site_changes_schema",
        title="Migrate pending-changes records to the new schema",
        # Runs before any action that records new changes itself, so a single
        # update pass leaves the journal entirely in the new schema.
        sort_index=10,
        expiry_version=ExpiryVersion.NEVER,
    )
)
