#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Sequence

import pytest

from tests.testlib.unit.utils import reset_registries

from cmk.gui import permissions
from cmk.gui.permissions import permission_registry, permission_section_registry


@pytest.fixture(name="reset_permission_registries")
def fixture_reset_permission_registries() -> Iterator[None]:
    """Fixture to reset registries to its default entries."""
    with reset_registries([permission_registry, permission_section_registry]):
        yield


@pytest.mark.usefixtures("reset_permission_registries")
def test_declare_permission_section(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        permissions, "permission_section_registry", permissions.PermissionSectionRegistry()
    )
    assert "bla" not in permissions.permission_section_registry
    permissions.declare_permission_section("bla", "bla perm", do_sort=False)
    assert "bla" in permissions.permission_section_registry

    section = permissions.permission_section_registry["bla"]
    assert section.title == "bla perm"
    assert section.sort_index == 50
    assert section.do_sort is False


@pytest.mark.usefixtures("reset_permission_registries")
def test_declare_permission(monkeypatch: pytest.MonkeyPatch) -> None:
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

    sec1 = permissions.PermissionSection(
        name="sec1",
        title="SEC1",
        do_sort=do_sort,
    )

    sections.register(sec1)

    for permission_name in ["Z", "z", "A", "b", "a", "1", "g"]:
        perms.register(
            permissions.Permission(
                section=sec1,
                name=permission_name,
                title=permission_name.title(),
                description="bla",
                defaults=["admin"],
            )
        )

    sorted_perms = [p.name for p in perms.get_sorted_permissions(sec1)]
    assert sorted_perms == result
