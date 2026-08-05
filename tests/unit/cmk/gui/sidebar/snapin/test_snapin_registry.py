#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from typing import cast

import pytest

from cmk.ccc.user import UserId
from cmk.gui import pagetypes
from cmk.gui.logged_in import user
from cmk.gui.sidebar._snapin._base import CustomizableSidebarSnapin
from cmk.gui.sidebar._snapin._registry import (
    custom_snapin_classes,
    CustomSnapinParamsConfig,
    CustomSnapinParamsRowConfig,
    CustomSnapins,
    CustomSnapinsConfig,
    snapin_registry,
    SnapinRegistry,
)
from cmk.gui.sidebar._snapin._tactical_overview import TacticalOverviewSnapin
from cmk.gui.type_defs import IconNames, StaticIcon
from cmk.gui.utils.roles import UserPermissions

USER_PERMISSIONS = UserPermissions({}, {}, {}, [])


@pytest.fixture(name="permissive_user", autouse=True)
def fixture_permissive_user(
    request_context: None, monkeypatch: pytest.MonkeyPatch
) -> Iterator[None]:
    with monkeypatch.context() as m:
        m.setattr(user, "may", lambda x: True)
        yield


def _custom_snapin(
    name: str,
    base_type: str,
    *,
    title: str = "My overview",
    description: str = "What I care about",
) -> CustomSnapins:
    return CustomSnapins(
        CustomSnapinsConfig(
            name=name,
            title=title,
            description=description,
            owner=UserId("harry"),
            public=False,
            hidden=False,
            custom_snapin=(
                base_type,
                CustomSnapinParamsConfig(
                    rows=[CustomSnapinParamsRowConfig(title="Hosts", query=("hosts", {}))],
                    show_failed_notifications=True,
                    show_sites_not_connected=True,
                    show_stale=True,
                ),
            ),
        )
    )


def test_type_metadata() -> None:
    assert CustomSnapins.type_name() == "custom_snapin"
    assert CustomSnapins.type_icon() == StaticIcon(IconNames.custom_snapin)
    assert CustomSnapins.type_is_show_more() is True


def test_phrases_are_element_flavoured() -> None:
    assert CustomSnapins.phrase("title") == "Custom sidebar element"
    assert CustomSnapins.phrase("new") == "Add element"


def test_phrase_falls_back_to_the_generic_wording() -> None:
    """Only the phrases the type overrides are its own; the rest must keep coming from the
    shared page-type wording."""
    assert CustomSnapins.phrase("add_to") == pagetypes.Base.phrase("add_to")


def test_serialize_deserialize_roundtrip() -> None:
    original = _custom_snapin("my_overview", "tactical_overview")

    assert CustomSnapins.deserialize(original.serialize()).config == original.config


def test_registry_plugin_name_is_the_snapin_type_name() -> None:
    assert SnapinRegistry().plugin_name(TacticalOverviewSnapin) == "tactical_overview"


def test_customizable_snapin_types_are_a_subset_of_all_types() -> None:
    customizable = dict(snapin_registry.get_customizable_snapin_types())

    assert "tactical_overview" in customizable
    assert "bookmarks" not in customizable
    assert all(
        issubclass(snapin_type, CustomizableSidebarSnapin) for snapin_type in customizable.values()
    )


def test_reserved_unique_ids_block_the_builtin_snapin_names() -> None:
    """A custom element may not shadow a built-in one, otherwise the built-in becomes
    unreachable in the sidebar."""
    reserved = CustomSnapins.reserved_unique_ids()

    assert "tactical_overview" in reserved
    assert "bookmarks" in reserved


def test_customizable_snapin_type_choices_are_sorted_by_id() -> None:
    choices = CustomSnapins._customizable_snapin_type_choices()
    idents = [str(choice[0]) for choice in choices]

    assert idents == sorted(idents)
    assert ("tactical_overview", TacticalOverviewSnapin.title()) in [
        (str(choice[0]), choice[1]) for choice in choices
    ]


def test_custom_snapin_classes_derives_from_the_base_snapin() -> None:
    classes = custom_snapin_classes([_custom_snapin("my_overview", "tactical_overview")])

    assert list(classes) == ["my_overview"]
    generated = classes["my_overview"]
    assert issubclass(generated, TacticalOverviewSnapin)
    assert generated.is_custom_snapin() is True
    assert generated.type_name() == "my_overview"
    assert generated.title() == "My overview"
    assert generated.description() == "What I care about"
    assert generated.permission_name() == "custom_snapin.my_overview"


def test_custom_snapin_classes_carry_the_configured_parameters() -> None:
    classes = custom_snapin_classes([_custom_snapin("my_overview", "tactical_overview")])

    parameters = cast(CustomSnapinParamsConfig, classes["my_overview"].parameters())  # type: ignore[attr-defined]

    assert [row.title for row in parameters.rows] == ["Hosts"]


def test_custom_snapin_classes_skips_an_unknown_base_type() -> None:
    """Custom elements survive the removal of the snap-in they were built on; they are
    dropped instead of crashing the sidebar."""
    assert custom_snapin_classes([_custom_snapin("my_overview", "no_such_snapin")]) == {}


def test_custom_snapin_classes_skips_a_non_customizable_base_type() -> None:
    assert custom_snapin_classes([_custom_snapin("my_bookmarks", "bookmarks")]) == {}


def test_custom_snapin_classes_rejects_a_bogus_registry_entry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with monkeypatch.context() as m:
        m.setattr(
            "cmk.gui.sidebar._snapin._registry.snapin_registry", {"tactical_overview": object}
        )
        with pytest.raises(ValueError, match="invalid snap-in type"):
            custom_snapin_classes([_custom_snapin("my_overview", "tactical_overview")])


def test_custom_snapin_classes_of_an_empty_list() -> None:
    assert custom_snapin_classes([]) == {}


def test_generated_class_visibility_follows_the_custom_element_permission() -> None:
    private = _custom_snapin("mine", "tactical_overview")
    generated = custom_snapin_classes([private])["mine"]

    assert generated.may_see(USER_PERMISSIONS) == private.is_permitted(USER_PERMISSIONS)
