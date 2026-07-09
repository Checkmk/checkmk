#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Tests for the Maps permission section + permissions."""

from cmk.gui.config import default_authorized_builtin_role_ids
from cmk.gui.permissions import (
    permission_registry as global_permission_registry,
)
from cmk.gui.permissions import PermissionRegistry, PermissionSectionRegistry
from cmk.maps.gui import _permissions


def _register() -> tuple[PermissionSectionRegistry, PermissionRegistry]:
    section_registry = PermissionSectionRegistry()
    permission_registry = PermissionRegistry()
    _permissions.register(section_registry, permission_registry)
    return section_registry, permission_registry


def test_registers_maps_section() -> None:
    section_registry, _perms = _register()
    assert "maps" in section_registry


def test_does_not_register_per_map_section() -> None:
    # The per-instance ``map.<name>`` section is declared by
    # ``pagetypes.declare(MapPage)``; registering it here too would raise.
    section_registry, _perms = _register()
    assert "map" not in section_registry


def test_registers_use_and_configure_permissions() -> None:
    _section, permission_registry = _register()
    assert set(permission_registry) == {"maps.use", "maps.configure"}


def test_use_permission_defaults_to_viewer_roles() -> None:
    _section, permission_registry = _register()
    assert permission_registry["maps.use"].defaults == list(default_authorized_builtin_role_ids)


def test_configure_permission_is_admin_only() -> None:
    _section, permission_registry = _register()
    assert permission_registry["maps.configure"].defaults == ["admin"]


def test_pagetype_declares_the_publish_permission_set(load_plugins: None) -> None:  # noqa: ARG001
    """``pagetypes.declare(MapPage)`` is what gives maps the publish model.

    Pinned here because the SPA's visibility form and the REST API's
    ``_authorized_public`` are written against exactly this set — losing one of
    them (or gaining one) silently changes who may share a map with whom.
    """
    assert {name for name in global_permission_registry if name.endswith("_map")} == {
        "general.edit_map",
        "general.publish_map",
        "general.publish_to_groups_map",
        "general.publish_to_foreign_groups_map",
        "general.publish_to_sites_map",
        "general.see_user_map",
        "general.force_map",
        "general.edit_foreign_map",
        "general.delete_foreign_map",
    }
