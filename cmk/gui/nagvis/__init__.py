#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Callable, Sequence

from cmk.gui import hooks, userdb
from cmk.gui.permissions import PermissionRegistry, PermissionSectionRegistry
from cmk.gui.sidebar._snapin._registry import SnapinRegistry
from cmk.gui.watolib.groups import (
    ContactGroupUsageFinderRegistry as ContactGroupUsageFinderRegistry,
)

from . import _auth_php, _hosttags, _nagvis_auth
from ._nagvis_maps import NagVisMaps


def register(
    permission_section_registry: PermissionSectionRegistry,
    permission_registry: PermissionRegistry,
    snapin_registry_: SnapinRegistry,
) -> None:
    _register_hooks()
    _nagvis_auth.register(permission_section_registry, permission_registry)
    snapin_registry_.register(NagVisMaps)


def _register_hooks() -> None:
    # TODO: Should we not execute this hook also when folders are modified?
    args: Sequence[tuple[str, Callable]] = (
        ("userdb-job", _auth_php._on_userdb_job),
        ("users-saved", lambda users: _auth_php._create_auth_file("users-saved", users)),
        ("roles-saved", lambda x: _auth_php._create_auth_file("roles-saved", userdb.load_users())),
        (
            "contactgroups-saved",
            lambda x: _auth_php._create_auth_file("contactgroups-saved", userdb.load_users()),
        ),
        (
            "activate-changes",
            lambda x: _auth_php._create_auth_file("activate-changes", userdb.load_users()),
        ),
        ("tags-saved", lambda x: _hosttags._export_hosttags_to_php(x)),
    )
    for name, func in args:
        hooks.register_builtin(name, func)
