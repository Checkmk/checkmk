#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.utils.plugin_registry import Registry

import cmk.gui.permissions as permissions
from cmk.gui.permissions import permission_registry, permission_section_registry


@pytest.fixture(name="registry_list", scope="module")
def fixture_registry_list() -> list[Registry]:
    """Returns 'permission_registry' and 'permission_section_registry'.

    Registries are to be reset after test-case execution.
    """
    return [permission_registry, permission_section_registry]


def test_declare_permission_section(
    reset_gui_registries: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        permissions, "permission_section_registry", permissions.PermissionSectionRegistry()
    )
    assert "bla" not in permissions.permission_section_registry
    permissions.declare_permission_section("bla", "bla perm", do_sort=False)
    assert "bla" in permissions.permission_section_registry

    section = permissions.permission_section_registry["bla"]()
    assert section.title == "bla perm"
    assert section.sort_index == 50
    assert section.do_sort is False


def test_declare_permission(reset_gui_registries: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        permissions, "permission_section_registry", permissions.PermissionSectionRegistry()
    )
    assert "bla" not in permissions.permission_section_registry
    permissions.declare_permission_section("bla", "bla perm", do_sort=False)
    assert "bla" in permissions.permission_section_registry

    monkeypatch.setattr(permissions, "permission_registry", permissions.PermissionRegistry())
    assert "bla.blub" not in permissions.permission_registry
    permissions.declare_permission("bla.blub", "bla perm", "descrrrrr", ["admin"])
    assert "bla.blub" in permissions.permission_registry

    permission = permissions.permission_registry["bla.blub"]
    assert permission.section == permissions.permission_section_registry["bla"]
    assert permission.name == "bla.blub"
    assert permission.title == "bla perm"
    assert permission.description == "descrrrrr"
    assert permission.defaults == ["admin"]


@pytest.mark.parametrize(
    "do_sort,result",
    [
        (True, ["sec1.1", "sec1.A", "sec1.a", "sec1.b", "sec1.g", "sec1.Z", "sec1.z"]),
        (False, ["sec1.Z", "sec1.z", "sec1.A", "sec1.b", "sec1.a", "sec1.1", "sec1.g"]),
    ],
)
def test_permission_sorting(do_sort: bool, result: Sequence[str]) -> None:
    sections = permissions.PermissionSectionRegistry()
    perms = permissions.PermissionRegistry()

    @sections.register
    class Sec1(permissions.PermissionSection):
        @property
        def name(self) -> str:
            return "sec1"

        @property
        def title(self) -> str:
            return "SEC1"

        @property
        def do_sort(self):
            return do_sort

    for permission_name in ["Z", "z", "A", "b", "a", "1", "g"]:
        perms.register(
            permissions.Permission(
                section=Sec1,
                name=permission_name,
                title=permission_name.title(),
                description="bla",
                defaults=["admin"],
            )
        )

    sorted_perms = [p.name for p in perms.get_sorted_permissions(Sec1())]
    assert sorted_perms == result
