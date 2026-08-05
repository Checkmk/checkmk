#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.gui.i18n import _l
from cmk.gui.main_menu import (
    any_show_more_items,
    get_main_menu_items_prefixed_by_segment,
    MainMenuRegistry,
)
from cmk.gui.main_menu_types import MainMenuItem, MainMenuLinkItem
from cmk.shared_typing.main_menu import (
    NavItemIdEnum,
    NavItemShortcut,
    NavItemTopic,
    NavItemTopicEntry,
    TopicItemMode,
)


def _entry(
    id_: str,
    title: str,
    *,
    mode: TopicItemMode | None = None,
    entries: Sequence[NavItemTopicEntry] | None = None,
    is_show_more: bool | None = None,
) -> NavItemTopicEntry:
    return NavItemTopicEntry(
        id=id_,
        title=title,
        sort_index=0,
        mode=mode,
        entries=entries,
        is_show_more=is_show_more,
    )


def _topic(entries: Sequence[NavItemTopicEntry]) -> NavItemTopic:
    return NavItemTopic(id="topic", title="Topic", sort_index=0, entries=entries)


def _menu_item(id_: NavItemIdEnum) -> MainMenuItem:
    return MainMenuItem(
        id=id_,
        title=_l("Some menu"),
        sort_index=0,
        shortcut=NavItemShortcut(key=id_.value[0]),
    )


def test_any_show_more_items_without_any_show_more_entry() -> None:
    assert any_show_more_items([_topic([_entry("a", "A"), _entry("b", "B")])]) is False


def test_any_show_more_items_with_a_show_more_entry() -> None:
    assert (
        any_show_more_items([_topic([_entry("a", "A"), _entry("b", "B", is_show_more=True)])])
        is True
    )


def test_any_show_more_items_of_topic_without_entries() -> None:
    assert any_show_more_items([_topic([])]) is False


def test_any_show_more_items_looks_at_every_topic() -> None:
    assert (
        any_show_more_items(
            [_topic([_entry("a", "A")]), _topic([_entry("b", "B", is_show_more=True)])]
        )
        is True
    )


def test_prefixed_by_segment_keeps_plain_entries_unprefixed() -> None:
    collected = get_main_menu_items_prefixed_by_segment(
        _topic([_entry("a", "A"), _entry("b", "B", mode=TopicItemMode.item)])
    )

    assert [(e.id, e.title) for e in collected] == [("a", "A"), ("b", "B")]


def test_prefixed_by_segment_without_entries() -> None:
    assert get_main_menu_items_prefixed_by_segment(_topic([])) == []


@pytest.mark.parametrize(
    "mode",
    [
        pytest.param(TopicItemMode.indented, id="indented"),
        pytest.param(TopicItemMode.multilevel, id="multilevel"),
    ],
)
def test_prefixed_by_segment_flattens_grouping_entries(mode: TopicItemMode) -> None:
    """An ``indented``/``multilevel`` entry is not an item itself - it only groups items.

    It is replaced by its children, each prefixed with the group's title."""
    collected = get_main_menu_items_prefixed_by_segment(
        _topic(
            [
                _entry("group", "Group", mode=mode, entries=[_entry("a", "A"), _entry("b", "B")]),
                _entry("c", "C"),
            ]
        )
    )

    assert [(e.id, e.title) for e in collected] == [
        ("a", "Group | A"),
        ("b", "Group | B"),
        ("c", "C"),
    ]


def test_prefixed_by_segment_drops_grouping_entry_without_children() -> None:
    collected = get_main_menu_items_prefixed_by_segment(
        _topic([_entry("group", "Group", mode=TopicItemMode.indented), _entry("a", "A")])
    )

    assert [(e.id, e.title) for e in collected] == [("a", "A")]


def test_prefixed_by_segment_uses_only_the_innermost_group_as_prefix() -> None:
    """Nesting does not accumulate prefixes: the recursion passes on the current group's
    title only, so a grandchild is prefixed with its direct parent, not the whole path."""
    collected = get_main_menu_items_prefixed_by_segment(
        _topic(
            [
                _entry(
                    "outer",
                    "Outer",
                    mode=TopicItemMode.indented,
                    entries=[
                        _entry(
                            "inner",
                            "Inner",
                            mode=TopicItemMode.indented,
                            entries=[_entry("a", "A")],
                        )
                    ],
                )
            ]
        )
    )

    assert [(e.id, e.title) for e in collected] == [("a", "Inner | A")]


def test_prefixed_by_segment_does_not_mutate_the_source_entry() -> None:
    """The prefixed titles must not leak back into the registered menu structure,
    which is shared between requests."""
    child = _entry("a", "A")
    topic = _topic([_entry("group", "Group", mode=TopicItemMode.indented, entries=[child])])

    collected = get_main_menu_items_prefixed_by_segment(topic)

    assert collected[0].title == "Group | A"
    assert child.title == "A"


@pytest.mark.parametrize(
    "accessor_name,menu_id",
    [
        pytest.param("menu_search", NavItemIdEnum.search, id="search"),
        pytest.param("menu_monitoring", NavItemIdEnum.monitoring, id="monitoring"),
        pytest.param("menu_customize", NavItemIdEnum.customize, id="customize"),
        pytest.param("menu_setup", NavItemIdEnum.setup, id="setup"),
        pytest.param("menu_help", NavItemIdEnum.help, id="help"),
        pytest.param("menu_activate", NavItemIdEnum.changes, id="changes"),
        pytest.param("menu_user", NavItemIdEnum.user, id="user"),
    ],
)
def test_registry_accessors_return_the_registered_item(
    accessor_name: str, menu_id: NavItemIdEnum
) -> None:
    registry = MainMenuRegistry()
    item = _menu_item(menu_id)
    registry.register(item)

    assert getattr(registry, accessor_name)() is item


def test_registry_plugin_name_is_the_item_id() -> None:
    registry = MainMenuRegistry()
    item = _menu_item(NavItemIdEnum.setup)

    assert registry.plugin_name(item) == NavItemIdEnum.setup


def test_registry_registers_under_the_item_id() -> None:
    registry = MainMenuRegistry()
    registry.register(_menu_item(NavItemIdEnum.help))

    assert list(registry) == [NavItemIdEnum.help]


def test_registry_accessor_rejects_a_link_item() -> None:
    """The ``menu_*`` accessors promise a ``MainMenuItem`` (one with topics). A link item
    registered under the same id would silently violate that, so it must be caught."""
    registry = MainMenuRegistry()
    registry.register(
        MainMenuLinkItem(
            id=NavItemIdEnum.help,
            title=_l("Help"),
            sort_index=0,
            shortcut=NavItemShortcut(key="h"),
        )
    )

    with pytest.raises(AssertionError):
        registry.menu_help()


def test_registry_accessor_raises_for_a_missing_menu() -> None:
    with pytest.raises(KeyError):
        MainMenuRegistry().menu_setup()
