#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Iterator, Sequence

import pytest

from cmk.gui import permissions
from cmk.gui.permissions import permission_registry, permission_section_registry
from tests.testlib.common.utils import reset_registries


@pytest.fixture(name="reset_permission_registries")
def fixture_reset_permission_registries() -> Iterator[None]:
    """Fixture to reset registries to its default entries."""
    with reset_registries([permission_registry]), reset_registries([permission_section_registry]):
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
    sec1 = permissions.PermissionSection(
        name="sec1",
        title="SEC1",
        do_sort=do_sort,
    )
    perms = permissions.PermissionRegistry()
    for permission_name in ["Z", "z", "A", "b", "a", "1", "g"]:
        perms.register(_permission(sec1, permission_name, title=permission_name.title()))

    sorted_perms = [p.name for p in permissions.get_sorted_permissions(perms, sec1)]
    assert sorted_perms == result


def test_permission_registered_again_is_sorted_by_its_last_registration() -> None:
    sec1 = permissions.PermissionSection(name="sec1", title="SEC1")
    perms = permissions.PermissionRegistry()
    perms.register(_permission(sec1, "a"))
    perms.register(_permission(sec1, "b"))
    perms.register(_permission(sec1, "a"))

    sorted_perms = [p.name for p in permissions.get_sorted_permissions(perms, sec1)]
    assert sorted_perms == ["sec1.b", "sec1.a"]


_SECTION = permissions.PermissionSection(name="sec", title="Section")
_OTHER_SECTION = permissions.PermissionSection(name="other", title="Other")


def _permission(
    section: permissions.PermissionSection, name: str, title: str = "title"
) -> permissions.Permission:
    return permissions.Permission(
        section=section, name=name, title=title, description="", defaults=["admin"]
    )


def _registry(*perms: permissions.Permission) -> permissions.PermissionRegistry:
    registry = permissions.PermissionRegistry()
    for perm in perms:
        registry.register(perm)
    return registry


class _CountingProvider:
    def __init__(self, perms: Iterable[permissions.Permission]) -> None:
        self._perms = list(perms)
        self.calls = 0

    def __call__(self) -> Iterable[permissions.Permission]:
        self.calls += 1
        return self._perms


def test_all_permissions_contains_static_and_dynamic_permissions() -> None:
    all_perms = permissions.AllPermissions(
        _registry(_permission(_SECTION, "static")),
        {"sec": [lambda: [_permission(_SECTION, "dynamic")]]},
    )

    assert list(all_perms) == ["sec.static", "sec.dynamic"]


def test_all_permissions_static_permission_wins_over_dynamic_one() -> None:
    static = _permission(_SECTION, "perm", title="static")
    all_perms = permissions.AllPermissions(
        _registry(static),
        {"sec": [lambda: [_permission(_SECTION, "perm", title="dynamic")]]},
    )

    assert list(all_perms.values()) == [static]


def test_all_permissions_static_lookup_does_not_compute_dynamic_permissions() -> None:
    provider = _CountingProvider([_permission(_SECTION, "dynamic")])
    all_perms = permissions.AllPermissions(
        _registry(_permission(_SECTION, "static")), {"sec": [provider]}
    )

    _ = all_perms["sec.static"]

    assert provider.calls == 0


def test_all_permissions_first_dynamic_declaration_wins() -> None:
    first = _permission(_SECTION, "perm", title="first")
    all_perms = permissions.AllPermissions(
        _registry(),
        {"sec": [lambda: [first], lambda: [_permission(_SECTION, "perm", title="second")]]},
    )

    assert list(all_perms.values()) == [first]


def test_all_permissions_lookup_only_computes_section_of_permission() -> None:
    other_provider = _CountingProvider([_permission(_OTHER_SECTION, "dynamic")])
    all_perms = permissions.AllPermissions(
        _registry(),
        {"sec": [lambda: [_permission(_SECTION, "dynamic")]], "other": [other_provider]},
    )

    _ = all_perms["sec.dynamic"]

    assert other_provider.calls == 0


def test_all_permissions_computes_section_once() -> None:
    provider = _CountingProvider([_permission(_SECTION, "dynamic")])
    all_perms = permissions.AllPermissions(_registry(), {"sec": [provider]})

    _ = all_perms["sec.dynamic"]
    _ = "sec.unknown" in all_perms

    assert provider.calls == 1


def test_all_permissions_does_not_modify_registry() -> None:
    registry = _registry()
    all_perms = permissions.AllPermissions(
        registry, {"sec": [lambda: [_permission(_SECTION, "dynamic")]]}
    )

    _ = all_perms["sec.dynamic"]

    assert "sec.dynamic" not in registry


def test_dynamic_permission_registry_registers_a_provider_once() -> None:
    registry = permissions.DynamicPermissionRegistry()
    provider = _CountingProvider([_permission(_SECTION, "dynamic")])

    registry.register("sec", provider)
    registry.register("sec", provider)

    assert list(registry["sec"]) == [provider]


def test_all_permissions_length_counts_static_and_dynamic_permissions() -> None:
    all_perms = permissions.AllPermissions(
        _registry(_permission(_SECTION, "static")),
        {"sec": [lambda: [_permission(_SECTION, "dynamic")]]},
    )

    assert len(all_perms) == 2
