#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""CLI to run the migration of NagVis maps into Checkmk Maps again."""

import argparse
import logging
import sys
from collections.abc import Sequence

from cmk.ccc.log import CMKFormatter
from cmk.ccc.site import omd_site
from cmk.ccc.version import edition
from cmk.gui import main_modules
from cmk.gui.config import active_config
from cmk.gui.session_context import SuperUserContext
from cmk.gui.site_config import get_login_sites, is_distributed_setup_remote_site
from cmk.gui.user_sites import activation_sites
from cmk.gui.watolib.audit_log import make_audit_log_change_hook
from cmk.gui.watolib.config_domain_name import CORE
from cmk.gui.watolib.pending_changes import (
    Change,
    ChangeScope,
    index_update_change_hook,
    PendingChanges,
    PendingChangesStore,
)
from cmk.gui.wsgi.app import gui_context
from cmk.update_config.plugins.actions.nagvis_maps import migrate_nagvis_maps
from cmk.utils import paths
from cmk.utils.redis import disable_redis

logger = logging.getLogger("cmk.update_config.migrate_maps")


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Migrate NagVis maps into Checkmk Maps, as the update does: each NagVis map "
            "not migrated yet becomes a map of the first admin. Maps migrated before are "
            "left untouched."
        ),
    )
    parser.add_argument(
        "maps",
        nargs="*",
        metavar="NAME",
        help="Migrate only these NagVis maps, named like their file without '.cfg'.",
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help=(
            "Also migrate the maps migrated before again, replacing their earlier result "
            "in Maps, also if it was changed there. Maps that existed before the "
            "migration are never replaced."
        ),
    )
    parser.add_argument("--debug", action="store_true", help="Raise errors instead of logging.")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    logger.addHandler(handler := logging.StreamHandler(stream=sys.stdout))
    handler.setFormatter(CMKFormatter(message_only=True))
    logger.setLevel(logging.INFO)
    main_modules.register(edition(paths.omd_root), debug=args.debug)

    with disable_redis(), gui_context(), SuperUserContext():
        if is_distributed_setup_remote_site(active_config.sites):
            logger.info(
                "This is a remote site. Maps are managed on the central site and "
                "synchronized from there. Run this tool there instead."
            )
            return 0
        try:
            result = migrate_nagvis_maps(logger, only=args.maps, force=args.force)
        except Exception:
            if args.debug:
                raise
            logger.exception("Migrating the NagVis maps failed")
            return 1
        if result.migrated:
            try:
                _add_change(len(result.migrated))
            except Exception:
                if args.debug:
                    raise
                logger.exception(
                    "The NagVis maps are migrated, but adding the pending change to activate "
                    "them failed. Running 'cmk-migrate-maps -f %(maps)s' adds it.",
                    {"maps": " ".join(result.migrated)},
                )
                return 1
    return 0 if result.complete else 1


def _add_change(migrated: int) -> None:
    """Let the next activation bring the maps and their role permissions to the sites."""
    PendingChanges(
        activation_sites=activation_sites(active_config.sites),
        local_site=omd_site(),
        acting_user=None,
        store=PendingChangesStore(),
        hooks=(
            make_audit_log_change_hook(use_git=active_config.wato_use_git),
            index_update_change_hook,
        ),
    ).add(
        Change(
            action_name="edit-roles",
            text=f"Migrated {migrated} NagVis map(s) into Checkmk Maps",
            domains=[CORE],
        ),
        ChangeScope.sites(get_login_sites(active_config.sites)),
    )


if __name__ == "__main__":
    sys.exit(main())
