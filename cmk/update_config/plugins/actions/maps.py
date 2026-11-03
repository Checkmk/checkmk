#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""One-time migration of OrbVis boards into Checkmk Maps.

See "Update from OrbVis" in ``doc/documentation/arch-comp-maps.rst``. What became
of each board, and the name each OrbVis icon got in Maps' library, is recorded in
``var/maps/legacy_maps_migration.mk``. A later run only looks at boards and icons not
recorded there, so an icon the operator deleted or replaced in Maps stays that way:

* ``migrated``: a board named like a shipped built-in map, another user's map or
  one of the admin's own becomes ``<name>_legacy``, shortened to fit, as the other
  would hide it, share its ``map.<name>`` permission or be overwritten,
* ``skipped``: the fallback name is taken too; the board is not imported over the
  map of it. Also an OrbVis demo board, which only showed OrbVis's features.

A board that could not be migrated is not recorded: every update tries it again,
so one fixed by hand comes over with the next run. The same goes for an icon the
copy left out.
"""

from collections.abc import Mapping, Sequence
from logging import Logger
from pathlib import Path
from typing import override

from cmk.ccc import store
from cmk.gui.role_types import UserRoleBase
from cmk.gui.userdb import load_users
from cmk.maps.gui._images import delete_background_files
from cmk.maps.gui.legacy_maps import (
    copy_legacy_background,
    copy_legacy_icons,
    foreign_connections,
    is_demo_map,
    is_hidden_map,
    legacy_icon_names,
    legacy_map_to_spec,
    legacy_maps_dir,
    read_legacy_map,
    used_connections,
)
from cmk.maps.gui.pagetype import MapPage
from cmk.maps.gui.type_defs import map_config_from_spec
from cmk.maps.rest_api.utils import map_from_spec, spec_from_map
from cmk.maps.shared.validators import is_valid_map_name
from cmk.update_config.internal import ExpiryVersion, UpdateAction
from cmk.update_config.plugins.lib.maps import (
    admin_maps,
    AdminMaps,
    base_role,
    migration_owner,
    set_map_permission,
    SITE_ADMIN,
)
from cmk.update_config.registry import update_action_registry
from cmk.utils import paths
from cmk.utils.log import VERBOSE

# The roles OrbVis granted ``orbvis.use``, ``orbvis.view_all`` and every
# ``orbvis.view_<board>`` to by default.
_LEGACY_VIEW_ROLES = frozenset({"admin", "user"})


def _record_path() -> Path:
    return paths.omd_root / "var" / "maps" / "legacy_maps_migration.mk"


def _save_record(
    outcomes: Mapping[str, str], icons: Mapping[str, str], pending: Mapping[str, str]
) -> None:
    store.save_object_to_file(
        _record_path(), {"boards": outcomes, "icons": icons, "pending": pending}
    )


def _grant_board_visibility(roles: Mapping[str, UserRoleBase], maps: Mapping[str, str]) -> bool:
    """Let exactly the roles see each map (by board) that could see the board in OrbVis."""
    changed = False
    for role_id, role in roles.items():
        base = base_role(role_id, role)
        permissions = role["permissions"]
        uses = _legacy_grants(permissions, base, "orbvis.use")
        sees_all = _legacy_grants(permissions, base, "orbvis.view_all")
        for board, name in maps.items():
            sees = uses and (sees_all or _legacy_grants(permissions, base, f"orbvis.view_{board}"))
            changed |= set_map_permission(role_id, role, name, sees)
    return changed


def _legacy_grants(permissions: Mapping[str, bool], base_role: str, permission: str) -> bool:
    return permissions.get(permission, base_role in _LEGACY_VIEW_ROLES)


def _prepare_maps(
    boards: Sequence[Path], maps: AdminMaps, icons: dict[str, str], logger: Logger
) -> dict[str, str]:
    """Add each board to the admin's maps; returns the map name each migrated board got.

    Skipped boards are entered into the outcomes right away; one that failed is left
    for the next run. Icons copied on the way are entered into ``icons``.
    """
    icon_names = legacy_icon_names(icons)
    # Copied with the first board to migrate, so demo boards alone bring in no icons.
    icons_copied = False
    foreign = foreign_connections()
    migrated: dict[str, str] = {}
    for path in boards:
        board = path.stem
        if not is_valid_map_name(board):
            logger.warning(
                "OrbVis board %(file)s is not migrated: %(name)r is not a valid map name. "
                "Every update tries again until the file is renamed or removed.",
                {"file": path.relative_to(paths.omd_root), "name": board},
            )
            continue
        name = maps.taken.target(board)
        if maps.taken.taken(name):
            logger.warning(
                "OrbVis board %(board)r is not migrated: a map named %(name)r already exists.",
                {"board": board, "name": name},
            )
            maps.outcomes[board] = "skipped"
            continue
        try:
            data = read_legacy_map(path)
            if is_demo_map(data):
                logger.info("OrbVis demo board %(board)r is not migrated.", {"board": board})
                maps.outcomes[board] = "skipped"
                continue
            if not icons_copied:
                # Checked first: a failing board is retried on every update and must not
                # copy the library and repeat its warnings each time.
                map_from_spec(legacy_map_to_spec(data, name, icon_names, foreign))
                icons.update(copy_legacy_icons(logger, icons))
                icon_names = legacy_icon_names(icons)
                icons_copied = True
            # Validated through the REST model, so a migrated map can never crash the
            # REST show/list serialisation.
            spec = spec_from_map(map_from_spec(legacy_map_to_spec(data, name, icon_names, foreign)))
            copy_legacy_background(spec, maps.admin, name, logger)
            cfg = map_config_from_spec(
                maps.admin, name, spec, public=True, hidden=is_hidden_map(data)
            )
            maps.own[name] = MapPage(cfg).serialize()
        except Exception as exc:
            logger.warning(
                "Could not migrate OrbVis board %(file)s: %(error)s. "
                "Every update tries again until the file is fixed or removed.",
                {"file": path.relative_to(paths.omd_root), "error": exc},
            )
            delete_background_files(maps.admin, name)
            continue
        migrated[board] = name
        if used_foreign := sorted(used_connections(spec) & foreign):
            logger.warning(
                "OrbVis board %(board)r uses the OrbVis connection(s) %(ids)s; add a "
                "connection of the same ID in the Maps settings.",
                {"board": board, "ids": ", ".join(used_foreign)},
            )
        if name != board:
            logger.warning(
                "OrbVis board %(board)r is migrated as %(name)r: a map of that name already exists.",
                {"board": board, "name": name},
            )
        logger.log(
            VERBOSE,
            "Prepared OrbVis board %(name)r for %(admin)s (published).",
            {"name": name, "admin": maps.admin},
        )
    return migrated


class MigrateLegacyMaps(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        boards_dir = legacy_maps_dir() / "boards"
        if not boards_dir.is_dir():
            return
        record = store.load_object_from_file(_record_path(), default={})
        outcomes: dict[str, str] = record.get("boards", {})
        icons: dict[str, str] = record.get("icons", {})
        boards = [path for path in sorted(boards_dir.glob("*.json")) if path.stem not in outcomes]
        if not boards:
            return

        admin = migration_owner(load_users())
        if admin is None:
            logger.warning(
                "Cannot migrate %(count)d OrbVis board(s): no user with the admin role "
                "found. They will be migrated by a later update once an admin exists.",
                {"count": len(boards)},
            )
            return

        with admin_maps(
            admin,
            record.get("pending", {}),
            outcomes,
            lambda outcomes, pending: _save_record(outcomes, icons, pending),
        ) as maps:
            boards = [path for path in boards if path.stem not in outcomes]
            migrated = _prepare_maps(boards, maps, icons, logger)
            maps.store(migrated, lambda roles: _grant_board_visibility(roles, migrated))

        if migrated:
            logger.info(
                "Migrated %(count)d OrbVis board(s) to %(admin)s (published).",
                {"count": len(migrated), "admin": admin},
            )
            if admin != SITE_ADMIN:
                logger.warning(
                    "The migrated OrbVis boards belong to %(admin)s, as there is no admin "
                    "%(site_admin)s. Deleting %(admin)s removes these maps.",
                    {"admin": admin, "site_admin": SITE_ADMIN},
                )


update_action_registry.register(
    MigrateLegacyMaps(
        name="migrate_legacy_maps",
        title="Migrate OrbVis boards into Checkmk Maps",
        # After the pagetype actions; needs the users + pagetype store loadable.
        sort_index=130,
        expiry_version=ExpiryVersion.NEVER,
    )
)
