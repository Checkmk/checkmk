#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from typing import override

import pytest

from cmk.gui.config import Config, default_authorized_builtin_role_ids
from cmk.gui.logged_in import user
from cmk.gui.sidebar._snapin._base import CustomizableSidebarSnapin, SidebarSnapin
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.valuespec import ValueSpec

USER_PERMISSIONS = UserPermissions({}, {}, {}, [])


class MinimalSnapin(SidebarSnapin):
    """A snap-in that implements nothing beyond the abstract contract."""

    @classmethod
    @override
    def type_name(cls) -> str:
        return "minimal"

    @classmethod
    @override
    def title(cls) -> str:
        return "Minimal"

    @classmethod
    @override
    def description(cls) -> str:
        return "Minimal snap-in"

    @override
    def show(self, config: Config) -> None:
        pass


class DelegatingSnapin(SidebarSnapin):
    """Delegates the abstract methods to the base class to pin down what it promises."""

    @classmethod
    @override
    def type_name(cls) -> str:
        return super().type_name()

    @classmethod
    @override
    def title(cls) -> str:
        return super().title()

    @classmethod
    @override
    def description(cls) -> str:
        return super().description()

    @override
    def show(self, config: Config) -> None:
        return super().show(config)  # type: ignore[safe-super]


class DelegatingCustomizableSnapin(CustomizableSidebarSnapin):
    @classmethod
    @override
    def type_name(cls) -> str:
        return "delegating_customizable"

    @classmethod
    @override
    def title(cls) -> str:
        return "Delegating"

    @classmethod
    @override
    def description(cls) -> str:
        return ""

    @override
    def show(self, config: Config) -> None:
        pass

    @classmethod
    @override
    def vs_parameters(cls) -> list[tuple[str, ValueSpec[object]]]:
        return super().vs_parameters()

    @classmethod
    @override
    def parameters(cls) -> object:
        return super().parameters()


@pytest.fixture(name="permissive_user", autouse=True)
def fixture_permissive_user(
    request_context: None, monkeypatch: pytest.MonkeyPatch
) -> Iterator[None]:
    with monkeypatch.context() as m:
        m.setattr(user, "may", lambda x: True)
        yield


def test_permission_name_is_derived_from_the_type_name() -> None:
    assert MinimalSnapin.permission_name() == "sidesnap.minimal"


def test_a_snapin_is_visible_to_the_default_roles() -> None:
    assert MinimalSnapin.allowed_roles() == default_authorized_builtin_role_ids


def test_may_see_asks_for_the_snapin_permission(monkeypatch: pytest.MonkeyPatch) -> None:
    with monkeypatch.context() as m:
        m.setattr(user, "may", lambda x: x != "sidesnap.minimal")
        assert MinimalSnapin.may_see(USER_PERMISSIONS) is False

    assert MinimalSnapin.may_see(USER_PERMISSIONS) is True


@pytest.mark.parametrize(
    "accessor,default",
    [
        pytest.param("has_show_more_items", False, id="has_show_more_items"),
        pytest.param("refresh_regularly", False, id="refresh_regularly"),
        pytest.param("refresh_on_restart", False, id="refresh_on_restart"),
        pytest.param("is_custom_snapin", False, id="is_custom_snapin"),
        pytest.param("included_in_default_sidebar", True, id="included_in_default_sidebar"),
    ],
)
def test_opt_in_behaviours_default_off(accessor: str, default: bool) -> None:
    """Every optional snap-in behaviour has to be opted into explicitly - a new snap-in must
    not start out refreshing or hiding itself from the default sidebar."""
    assert getattr(MinimalSnapin, accessor)() is default


def test_a_snapin_has_no_styles_by_default() -> None:
    assert MinimalSnapin().styles() is None


def test_a_snapin_registers_no_page_handlers_by_default() -> None:
    assert MinimalSnapin().page_handlers() == {}


@pytest.mark.parametrize(
    "accessor",
    [
        pytest.param("type_name", id="type_name"),
        pytest.param("title", id="title"),
        pytest.param("description", id="description"),
    ],
)
def test_the_abstract_classmethods_have_no_usable_default(accessor: str) -> None:
    with pytest.raises(NotImplementedError):
        getattr(DelegatingSnapin, accessor)()


def test_show_has_no_usable_default(load_config: Config) -> None:
    with pytest.raises(NotImplementedError):
        DelegatingSnapin().show(load_config)


@pytest.mark.parametrize(
    "accessor",
    [
        pytest.param("vs_parameters", id="vs_parameters"),
        pytest.param("parameters", id="parameters"),
    ],
)
def test_a_customizable_snapin_must_declare_its_parameters(accessor: str) -> None:
    with pytest.raises(NotImplementedError):
        getattr(DelegatingCustomizableSnapin, accessor)()


def test_a_customizable_snapin_is_still_a_snapin() -> None:
    assert issubclass(CustomizableSidebarSnapin, SidebarSnapin)
