#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""One-time migration of OrbVis boards into Checkmk Maps.

See "Update from OrbVis" in ``doc/documentation/arch-comp-maps.rst``. What became
of each board, and the name each OrbVis icon got in Maps' library, is recorded in
``var/maps/legacy_maps_migration.mk``. A later run only looks at boards and icons not
recorded there, so an icon the operator deleted or replaced in Maps stays that way:

* ``migrated``: a board named like a shipped built-in map or another user's map
  becomes ``<name>_legacy``, as the other would hide it or share its
  ``map.<name>`` permission,
* ``skipped``: the admin already has a map of that name, or the fallback name is
  taken too; the board is not imported over it. Also an OrbVis demo board, which
  only showed OrbVis's features.

A board that could not be migrated is not recorded: every update tries it again,
so one fixed by hand comes over with the next run. The same goes for an icon the
copy left out.
"""

from collections.abc import Mapping, Sequence
from contextlib import suppress
from logging import Logger
from pathlib import Path
from typing import override

from cmk.ccc import store
from cmk.ccc.user import UserId
from cmk.gui.config import active_config, default_authorized_builtin_role_ids
from cmk.gui.logged_in import save_user_file
from cmk.gui.role_types import UserRoleBase
from cmk.gui.type_defs import Users
from cmk.gui.userdb import load_users, UserRolesConfigFile
from cmk.maps.gui.legacy_maps import (
    copy_legacy_background,
    copy_legacy_icons,
    drop_legacy_background,
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
from cmk.maps.gui.store import is_valid_map_name, user_maps_path
from cmk.maps.gui.type_defs import map_config_from_spec
from cmk.maps.rest_api.utils import map_from_spec, spec_from_map
from cmk.update_config.internal import ExpiryVersion, UpdateAction
from cmk.update_config.registry import update_action_registry
from cmk.utils import paths
from cmk.utils.log import VERBOSE

_ADMIN_ROLE = "admin"

_SITE_ADMIN = UserId("cmkadmin")

# The roles OrbVis granted ``orbvis.use``, ``orbvis.view_all`` and every
# ``orbvis.view_<board>`` to by default.
_LEGACY_VIEW_ROLES = frozenset({"admin", "user"})


def _record_path() -> Path:
    return paths.omd_root / "var" / "maps" / "legacy_maps_migration.mk"


def _save_record(outcomes: Mapping[str, str], icons: Mapping[str, str]) -> None:
    store.save_object_to_file(_record_path(), {"boards": outcomes, "icons": icons})


def _migration_owner(users: Users) -> UserId | None:
    """``cmkadmin``, else the lowest-sorted human user holding the built-in admin role.

    Automation users are excluded so the migrated maps end up owned by a real
    operator (``load_users`` stamps ``is_automation_user`` on every user). Deleting
    the owner removes its maps, and ``cmkadmin`` tends to outlive personal accounts;
    a locked one still counts, as others see and edit its maps by its roles. Another
    locked admin only when no other is left: it is likely deleted later."""
    admins = [
        user_id
        for user_id, attr in users.items()
        if not attr.get("is_automation_user", False) and _ADMIN_ROLE in (attr.get("roles") or [])
    ]
    return min(
        admins,
        key=lambda user_id: (
            user_id != _SITE_ADMIN,
            users[user_id].get("locked", False),
            user_id,
        ),
        default=None,
    )


def _grant_board_visibility(roles: Mapping[str, UserRoleBase], maps: Mapping[str, str]) -> bool:
    """Let exactly the roles see each map (by board) that could see the board in OrbVis.

    Only a role whose answer differs from the map permission's default gets an
    explicit ``map.<name>`` entry, so the defaults keep applying everywhere else. An
    entry left over from an earlier map of the same name is dropped.
    """
    changed = False
    for role_id, role in roles.items():
        base = str(role.get("basedon") or role_id)
        permissions = role["permissions"]
        map_default = base in default_authorized_builtin_role_ids
        uses = _legacy_grants(permissions, base, "orbvis.use")
        sees_all = _legacy_grants(permissions, base, "orbvis.view_all")
        for board, name in maps.items():
            sees = uses and (sees_all or _legacy_grants(permissions, base, f"orbvis.view_{board}"))
            key = f"map.{name}"
            if sees != map_default:
                permissions[key] = sees
                changed = True
            elif permissions.pop(key, None) is not None:
                changed = True
    return changed


def _legacy_grants(permissions: Mapping[str, bool], base_role: str, permission: str) -> bool:
    return permissions.get(permission, base_role in _LEGACY_VIEW_ROLES)


def _prepare_maps(
    boards: Sequence[Path],
    admin: UserId,
    own: dict[str, dict[str, object]],
    outcomes: dict[str, str],
    icons: dict[str, str],
    logger: Logger,
) -> dict[str, str]:
    """Add each board to ``own`` as a map; returns the map name each migrated board got.

    Skipped boards are entered into ``outcomes`` right away; one that failed is left
    for the next run. Icons copied on the way are entered into ``icons``.
    """
    builtins = MapPage.builtin_pages()
    # Only the names: another user's map of a name shares its map.<name> permission.
    others = {name for owner, name in MapPage.load_raw() if owner != admin}
    icon_names = legacy_icon_names(icons)
    # Copied with the first board to migrate, so demo boards alone bring in no icons.
    icons_copied = False
    foreign = foreign_connections()
    migrated: dict[str, str] = {}
    for path in boards:
        board = path.stem
        # A fixed fallback, so a rerun after a stopped run finds it and skips.
        name = f"{board}_legacy" if board in builtins or board in others else board
        if not is_valid_map_name(name):
            logger.warning(
                "OrbVis board %(file)s is not migrated: %(name)r is not a valid map name. "
                "Every update tries again until the file is renamed or removed.",
                {"file": path.relative_to(paths.omd_root), "name": name},
            )
            continue
        if name in builtins or name in others or name in own:
            logger.warning(
                "OrbVis board %(board)r is not migrated: a map named %(name)r already exists.",
                {"board": board, "name": name},
            )
            outcomes[board] = "skipped"
            continue
        try:
            data = read_legacy_map(path)
            if is_demo_map(data):
                logger.info("OrbVis demo board %(board)r is not migrated.", {"board": board})
                outcomes[board] = "skipped"
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
            copy_legacy_background(spec, admin, name, logger)
            cfg = map_config_from_spec(admin, name, spec, public=True, hidden=is_hidden_map(data))
            own[name] = MapPage(cfg).serialize()
        except Exception as exc:
            logger.warning(
                "Could not migrate OrbVis board %(file)s: %(error)s. "
                "Every update tries again until the file is fixed or removed.",
                {"file": path.relative_to(paths.omd_root), "error": exc},
            )
            drop_legacy_background(admin, name)
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
                "OrbVis board %(board)r is migrated as %(name)r: another map has its name.",
                {"board": board, "name": name},
            )
        logger.log(
            VERBOSE,
            "Prepared OrbVis board %(name)r for %(admin)s (published).",
            {"name": name, "admin": admin},
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

        admin = _migration_owner(load_users())
        if admin is None:
            logger.warning(
                "Cannot migrate %(count)d OrbVis board(s): no user with the admin role "
                "found. They will be migrated by a later update once an admin exists.",
                {"count": len(boards)},
            )
            return

        maps_path = user_maps_path(admin)
        with store.locked(maps_path):
            # The admin's stored maps as they are on disk: ``MapPage.load`` skips one
            # it cannot deserialize, and writing that set back would drop it.
            own: dict[str, dict[str, object]] = store.load_object_from_file(maps_path, default={})
            migrated = _prepare_maps(boards, admin, own, outcomes, icons, logger)
            # Settled already, whatever the saves below do.
            _save_record(outcomes, icons)
            if migrated:
                try:
                    # Roles first: a run stopping in between must not leave a published
                    # map open to everyone, as the next run skips an existing map.
                    roles_file = UserRolesConfigFile()
                    roles = roles_file.load_for_modification()
                    if _grant_board_visibility(roles, migrated):
                        roles_file.save(roles, pprint_value=active_config.wato_pprint_config)
                    save_user_file(maps_path.stem, own, admin)
                except Exception:
                    # Nothing stored: the next run copies them again, and for another
                    # owner these would be orphaned.
                    for name in migrated.values():
                        with suppress(OSError):
                            drop_legacy_background(admin, name)
                    raise
                outcomes.update(dict.fromkeys(migrated, "migrated"))
                _save_record(outcomes, icons)

        if migrated:
            logger.info(
                "Migrated %(count)d OrbVis board(s) to %(admin)s (published).",
                {"count": len(migrated), "admin": admin},
            )
            if admin != _SITE_ADMIN:
                logger.warning(
                    "The migrated OrbVis boards belong to %(admin)s, as there is no admin "
                    "%(site_admin)s. Deleting %(admin)s removes these maps.",
                    {"admin": admin, "site_admin": _SITE_ADMIN},
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
