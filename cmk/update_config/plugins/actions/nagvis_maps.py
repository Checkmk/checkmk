#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""One-time migration of NagVis maps into Checkmk Maps.

See "Update from NagVis" in ``doc/documentation/arch-comp-maps.rst``. What became of
each map, ``migrated`` or ``skipped``, is recorded in
``var/maps/nagvis_maps_migration.mk``; a later run only looks at maps not recorded
there. A map that could not be migrated is not recorded, so every update tries it
again.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from logging import Logger
from pathlib import Path
from typing import override

from cmk.ccc import store
from cmk.gui.config import default_authorized_builtin_role_ids
from cmk.gui.permissions import permission_registry
from cmk.gui.role_types import UserRoleBase
from cmk.gui.type_defs import VisualPublic
from cmk.gui.userdb import load_users, UserRolesConfigFile
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.watolib.groups_io import load_contact_group_information
from cmk.maps.gui._cfg_import import map_name_from_filename
from cmk.maps.gui._images import delete_background_files
from cmk.maps.gui.nagvis_maps import (
    copy_nagvis_background,
    nagvis_maps_dir,
    NagVisConfig,
    read_nagvis_config,
    read_nagvis_map,
    ShapeCopies,
)
from cmk.maps.gui.pagetype import MapPage
from cmk.maps.gui.type_defs import map_config_from_spec
from cmk.maps.rest_api.utils import map_from_spec, spec_from_map
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


def _record_path() -> Path:
    return paths.omd_root / "var" / "maps" / "nagvis_maps_migration.mk"


def _save_record(outcomes: Mapping[str, str], pending: Mapping[str, str]) -> None:
    store.save_object_to_file(_record_path(), {"maps": outcomes, "pending": pending})


@dataclass(frozen=True)
class _NagVisAccess:
    """Who could see NagVis maps, by role."""

    # ``nagvis.*_*_*`` or ``nagvis.Map_view_*``: every map.
    sees_all: frozenset[str]
    # ``nagvis.Map_view`` only: the maps a contact group of the user lists.
    by_group: frozenset[str]
    # Of these, the roles that may not see a published map in Maps at all.
    without_maps: frozenset[str]
    # The maps each contact group lists, by NagVis name.
    group_maps: Mapping[str, frozenset[str]]


def _nagvis_access() -> _NagVisAccess:
    roles = UserRolesConfigFile().load_for_reading()
    permissions = UserPermissions(roles, permission_registry, {}, [])

    def may(role_id: str, permission: str) -> bool:
        return permissions.may_with_roles([role_id], permission)

    sees_all = frozenset(
        role_id
        for role_id in roles
        if may(role_id, "nagvis.*_*_*") or may(role_id, "nagvis.Map_view_*")
    )
    by_group = frozenset(
        role_id for role_id in roles if role_id not in sees_all and may(role_id, "nagvis.Map_view")
    )
    return _NagVisAccess(
        sees_all=sees_all,
        by_group=by_group,
        without_maps=frozenset(
            role_id
            for role_id in sees_all | by_group
            if not (may(role_id, "maps.use") and may(role_id, "general.see_user_map"))
        ),
        group_maps={
            group_id: frozenset(str(name) for name in group.get("nagvis_maps", []))
            for group_id, group in load_contact_group_information().items()
        },
    )


def _map_access(
    nagvis_name: str, access: _NagVisAccess
) -> tuple[VisualPublic, frozenset[str], str | None]:
    """How to publish the map, and the roles to let see it, for the users who saw it.

    Maps lets a user see a map by a role *and* a contact group, never by either. A map
    NagVis showed to some roles by themselves and to others by a contact group is
    published to the groups, so it never reaches more users than in NagVis.
    """
    groups = sorted(group for group, names in access.group_maps.items() if nagvis_name in names)
    if not groups or not access.by_group:
        return True, access.sees_all, None
    public: VisualPublic = ("contact_groups", groups)
    if not access.sees_all:
        return public, access.by_group, None
    return (
        public,
        access.sees_all | access.by_group,
        (
            f"Users of the role(s) {', '.join(sorted(access.sees_all))} saw it in NagVis "
            "like every NagVis map. In Maps they see it only as members of the contact "
            f"group(s) {', '.join(groups)}, which it is published to."
        ),
    )


def _grant_map_visibility(
    roles: Mapping[str, UserRoleBase], seeing: Mapping[str, frozenset[str] | None]
) -> bool:
    changed = False
    for role_id, role in roles.items():
        default = base_role(role_id, role) in default_authorized_builtin_role_ids
        for name, role_ids in seeing.items():
            sees = default if role_ids is None else role_id in role_ids
            changed |= set_map_permission(role_id, role, name, sees)
    return changed


@dataclass
class _Migrated:
    # The Maps name each migrated map got, by NagVis name.
    names: dict[str, str] = field(default_factory=dict)
    # The roles to let see each map, by Maps name. ``None`` for a private map: its
    # permission keeps its default, without an entry left from an earlier map.
    seeing: dict[str, frozenset[str] | None] = field(default_factory=dict)
    shapes: ShapeCopies = field(default_factory=ShapeCopies)


def _prepare_maps(
    files: Sequence[Path],
    maps: AdminMaps,
    config: NagVisConfig,
    access: _NagVisAccess | None,
    logger: Logger,
) -> _Migrated:
    """Add each NagVis map to the admin's maps; skipped ones enter the outcomes.

    A map that failed is left for the next run. Without ``access`` the maps stay
    private to the admin.
    """
    migrated = _Migrated()
    for path in files:
        nagvis_name = path.stem
        # NagVis allows more characters in a map name, a dot for one.
        valid_name = map_name_from_filename(path.name)
        name = maps.taken.target(valid_name)
        if maps.taken.taken(name):
            logger.warning(
                "NagVis map %(map)r is not migrated: a map named %(name)r already exists.",
                {"map": nagvis_name, "name": name},
            )
            maps.outcomes[nagvis_name] = "skipped"
            continue
        try:
            map_cfg, warnings = read_nagvis_map(path, name, config)
            # Checked first, so a map that fails copies no background on every update.
            map_from_spec(dict(map_cfg))
            shape_names, shape_warnings = migrated.shapes.plan(map_cfg)
            warnings += shape_warnings
            warnings += copy_nagvis_background(map_cfg, maps.admin)
            # Validated through the REST model, so a migrated map can never crash the
            # REST show/list serialisation.
            spec = spec_from_map(map_from_spec(dict(map_cfg)))
        except Exception as exc:
            logger.warning(
                "Could not migrate NagVis map %(file)s: %(error)s. "
                "Every update tries again until the file is fixed or removed.",
                {"file": path.relative_to(paths.omd_root), "error": exc},
            )
            delete_background_files(maps.admin, name)
            continue
        public: VisualPublic = False
        migrated.seeing[name] = None
        if access is not None:
            public, migrated.seeing[name], access_warning = _map_access(nagvis_name, access)
            if access_warning:
                warnings.append(access_warning)
        maps.own[name] = MapPage(
            map_config_from_spec(maps.admin, name, spec, public=public)
        ).serialize()
        migrated.names[nagvis_name] = name
        migrated.shapes.used |= shape_names
        if valid_name != nagvis_name:
            warnings.append(
                f"Its name becomes {valid_name!r}, as a map name takes only letters, digits, "
                "underscores and hyphens."
            )
        if name != valid_name:
            warnings.append(f"It is migrated as {name!r}: a map of that name already exists.")
        for warning in warnings:
            logger.warning(
                "NagVis map %(map)r: %(warning)s", {"map": nagvis_name, "warning": warning}
            )
        logger.log(
            VERBOSE,
            "Prepared NagVis map %(name)r for %(admin)s.",
            {"name": name, "admin": maps.admin},
        )
    return migrated


class MigrateNagVisMaps(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        maps_dir = nagvis_maps_dir()
        if not maps_dir.is_dir():
            return
        record = store.load_object_from_file(_record_path(), default={})
        outcomes: dict[str, str] = record.get("maps", {})
        files = [path for path in sorted(maps_dir.glob("*.cfg")) if path.stem not in outcomes]
        if not files:
            return

        admin = migration_owner(load_users())
        if admin is None:
            logger.warning(
                "Cannot migrate %(count)d NagVis map(s): no user with the admin role "
                "found. They will be migrated by a later update once an admin exists.",
                {"count": len(files)},
            )
            return

        config = read_nagvis_config()
        access = _nagvis_access() if config.checkmk_permissions else None
        with admin_maps(admin, record.get("pending", {}), outcomes, _save_record) as maps:
            files = [path for path in files if path.stem not in outcomes]
            migrated = _prepare_maps(files, maps, config, access, logger)
            shape_warnings = maps.store(
                migrated.names,
                lambda roles: _grant_map_visibility(roles, migrated.seeing),
                migrated.shapes,
            )

        for warning in shape_warnings:
            logger.warning(warning)
        if not migrated.names:
            return
        logger.info(
            "Migrated %(count)d NagVis map(s) to %(admin)s.",
            {"count": len(migrated.names), "admin": admin},
        )
        if admin != SITE_ADMIN:
            logger.warning(
                "The migrated NagVis maps belong to %(admin)s, as there is no admin "
                "%(site_admin)s. Deleting %(admin)s removes these maps.",
                {"admin": admin, "site_admin": SITE_ADMIN},
            )
        if access is None:
            logger.warning(
                "NagVis does not use the Checkmk roles and contact groups for access on "
                "this site. The migrated maps are visible only to %(admin)s; publish them "
                "in Maps as needed.",
                {"admin": admin},
            )
        elif lacking := sorted(
            role_id
            for role_id in access.without_maps
            if any(seeing and role_id in seeing for seeing in migrated.seeing.values())
        ):
            logger.warning(
                "The role(s) %(roles)s could see NagVis maps, but lack the permission "
                "'Use Checkmk Maps' or 'See user maps' and do not see them in Maps.",
                {"roles": ", ".join(lacking)},
            )
        for pool, spec in sorted(config.pools.items()):
            if spec.urls and spec.maps & migrated.names.keys():
                logger.warning(
                    "The NagVis rotation pool %(pool)r also shows %(urls)s. Maps rotates "
                    "only through maps and leaves these out.",
                    {"pool": pool, "urls": ", ".join(spec.urls)},
                )


update_action_registry.register(
    MigrateNagVisMaps(
        name="migrate_nagvis_maps",
        title="Migrate NagVis maps into Checkmk Maps",
        # After the OrbVis migration, whose boards keep their names.
        sort_index=131,
        expiry_version=ExpiryVersion.NEVER,
    )
)
