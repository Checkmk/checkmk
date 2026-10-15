#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""What the migrations of OrbVis boards and NagVis maps into Checkmk Maps share."""

from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from typing import Protocol, Self

from cmk.ccc import store
from cmk.ccc.user import UserId
from cmk.gui.config import active_config, default_authorized_builtin_role_ids
from cmk.gui.logged_in import save_user_file
from cmk.gui.role_types import UserRoleBase
from cmk.gui.type_defs import Users
from cmk.gui.userdb import UserRolesConfigFile
from cmk.maps.gui._images import delete_background_files
from cmk.maps.gui.pagetype import MapPage
from cmk.maps.gui.store import user_maps_path
from cmk.maps.shared.map_name import MAP_NAME_MAX_LENGTH

_ADMIN_ROLE = "admin"

_FALLBACK_SUFFIX = "_legacy"

SITE_ADMIN = UserId("cmkadmin")


def migration_owner(users: Users) -> UserId | None:
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
            user_id != SITE_ADMIN,
            users[user_id].get("locked", False),
            user_id,
        ),
        default=None,
    )


@dataclass(frozen=True)
class TakenNames:
    """The map names a migrated map of ``admin`` must not take."""

    builtins: frozenset[str]
    # Only the names: another user's map of a name shares its map.<name> permission.
    others: frozenset[str]
    # The admin's own maps, including those migrated so far.
    own: Mapping[str, object]

    @classmethod
    def load(cls, admin: UserId, own: Mapping[str, object]) -> Self:
        return cls(
            builtins=frozenset(MapPage.builtin_pages()),
            others=frozenset(name for owner, name in MapPage.load_raw() if owner != admin),
            own=own,
        )

    def target(self, source: str) -> str:
        """The name ``source`` migrates as: ``<source>_legacy`` if a map has its name,
        as a built-in would hide it, another user's map share its permission and an
        own map be overwritten. ``source`` is shortened so the suffix still fits."""
        if not self.taken(source):
            return source
        return source[: MAP_NAME_MAX_LENGTH - len(_FALLBACK_SUFFIX)] + _FALLBACK_SUFFIX

    def taken(self, name: str) -> bool:
        return name in self.builtins or name in self.others or name in self.own


class MigratedFiles(Protocol):
    """Files a run adds next to its maps, such as NagVis shapes."""

    def store(self) -> list[str]:
        """Add the files; returns a warning for each that could not be added."""
        ...

    def remove_added(self) -> None:
        """Remove the files ``store`` added that were not there before."""
        ...


@dataclass(frozen=True)
class AdminMaps:
    """The admin's stored maps while ``admin_maps`` holds their lock."""

    admin: UserId
    own: dict[str, dict[str, object]]
    # What became of each source; the migrated are entered by ``store``.
    outcomes: dict[str, str]
    # Its ``own`` grows by each map a run migrates.
    taken: TakenNames
    save_record: Callable[[Mapping[str, str], Mapping[str, str]], None]

    def store(
        self,
        migrated: Mapping[str, str],
        grant: Callable[[Mapping[str, UserRoleBase]], bool],
        shapes: MigratedFiles | None = None,
    ) -> list[str]:
        """Store ``own``, with ``migrated`` (map name by source) among them, after
        ``grant`` let the roles see these and their ``shapes`` were added, and record
        the outcomes; returns a warning for each shape that could not be added.

        The record notes the migrated as pending first: a run stopping before it is
        final leaves them to the next to settle. Roles come before the maps: a run
        stopping in between must not leave a published map open to everyone, as the
        next run takes a stored map as migrated; so do the shapes, which it would not
        add again. On failure the backgrounds copied for the migrated maps and the
        shapes added are removed: the next run copies them again, and for another
        owner these would be orphaned. Shapes a stopped run added are not among
        them; the next run that stores the maps uses them.
        """
        if not migrated:
            self.save_record(self.outcomes, {})
            return []
        try:
            self.save_record(self.outcomes, migrated)
            warnings = shapes.store() if shapes else []
            roles_file = UserRolesConfigFile()
            roles = roles_file.load_for_modification()
            if grant(roles):
                roles_file.save(roles, pprint_value=active_config.wato_pprint_config)
            save_user_file(user_maps_path(self.admin).stem, self.own, self.admin)
        except Exception:
            for name in migrated.values():
                with suppress(OSError):
                    delete_background_files(self.admin, name)
            if shapes:
                shapes.remove_added()
            raise
        self.outcomes.update(dict.fromkeys(migrated, "migrated"))
        self.save_record(self.outcomes, {})
        return warnings


@contextmanager
def admin_maps(
    admin: UserId,
    pending: Mapping[str, str],
    outcomes: dict[str, str],
    save_record: Callable[[Mapping[str, str], Mapping[str, str]], None],
) -> Iterator[AdminMaps]:
    """The admin's stored maps, locked, with what a stopped run stored entered into
    ``outcomes``; the rest is tried again.

    Before storing, a run notes in ``pending`` the name each source is stored as. That
    name was free then, so a map of it among the admin's own is the one stored.
    ``save_record(outcomes, pending)`` writes the run's record.
    """
    maps_path = user_maps_path(admin)
    with store.locked(maps_path):
        # As they are on disk: ``MapPage.load`` skips one it cannot deserialize, and
        # writing that set back would drop it.
        own: dict[str, dict[str, object]] = store.load_object_from_file(maps_path, default={})
        for source, name in pending.items():
            if name in own:
                outcomes[source] = "migrated"
        yield AdminMaps(admin, own, outcomes, TakenNames.load(admin, own), save_record)


def base_role(role_id: str, role: UserRoleBase) -> str:
    """The built-in role whose permission defaults ``role`` has."""
    return str(role.get("basedon") or role_id)


def set_map_permission(role_id: str, role: UserRoleBase, name: str, sees: bool) -> bool:
    """Let the role see the map ``name`` or not; returns whether the role changed.

    Only an answer that differs from the map permission's default gets an explicit
    ``map.<name>`` entry, so the defaults keep applying everywhere else. An entry left
    over from an earlier map of the same name is dropped.
    """
    key = f"map.{name}"
    if sees != (base_role(role_id, role) in default_authorized_builtin_role_ids):
        role["permissions"][key] = sees
        return True
    return role["permissions"].pop(key, None) is not None
