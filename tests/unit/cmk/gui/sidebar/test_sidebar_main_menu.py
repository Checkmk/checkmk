#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
from collections.abc import Iterable, Iterator, Sequence

import pytest

from cmk.gui import message
from cmk.gui.config import Config
from cmk.gui.exceptions import MKAuthException, MKUserError
from cmk.gui.http import request
from cmk.gui.i18n import _l
from cmk.gui.logged_in import user
from cmk.gui.main_menu import MainMenuRegistry
from cmk.gui.main_menu_types import ConfigurableMainMenuItem, MainMenuItem, MainMenuLinkItem
from cmk.gui.pages import PageContext
from cmk.gui.sidebar.main_menu import (
    ajax_message_read,
    MainMenuConfigCreator,
    PageAjaxSidebarGetMessages,
    PageAjaxSidebarGetUnackIncompWerks,
    PageAjaxSitesAndChanges,
)
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.roles import UserPermissions
from cmk.shared_typing.main_menu import (
    NavItem,
    NavItemHeader,
    NavItemIdEnum,
    NavItemShortcut,
    NavItemTopic,
    NavItemTopicEntry,
    NavItemType,
    NavItemVueApp,
    NavLinkItem,
    NavVueAppIdEnum,
    TopicItemMode,
)

USER_PERMISSIONS = UserPermissions({}, {}, {}, [])


@pytest.fixture(name="permissive_user", autouse=True)
def fixture_permissive_user(
    request_context: None, monkeypatch: pytest.MonkeyPatch
) -> Iterator[None]:
    with monkeypatch.context() as m:
        m.setattr(user, "may", lambda x: True)
        yield


def _entry(
    id_: str,
    title: str,
    *,
    mode: TopicItemMode | None = None,
    entries: Sequence[NavItemTopicEntry] | None = None,
    sort_index: float = 0,
    url: str | None = "view.py",
) -> NavItemTopicEntry:
    return NavItemTopicEntry(
        id=id_,
        title=title,
        sort_index=sort_index,
        url=url,
        mode=mode,
        entries=entries,
    )


def _topic(entries: Sequence[NavItemTopicEntry], *, is_show_more: bool = False) -> NavItemTopic:
    return NavItemTopic(
        id="topic", title="Topic", sort_index=0, entries=entries, is_show_more=is_show_more
    )


def _item(
    id_: NavItemIdEnum,
    **kwargs: object,
) -> MainMenuItem:
    defaults: dict[str, object] = {
        "id": id_,
        "title": _l("Some menu"),
        "sort_index": 0,
        "shortcut": NavItemShortcut(key=id_.value[0]),
    }
    defaults.update(kwargs)
    return MainMenuItem(**defaults)  # type: ignore[arg-type]


def _search_item() -> MainMenuItem:
    return _item(
        NavItemIdEnum.search,
        get_vue_app=lambda req: NavItemVueApp(id=NavVueAppIdEnum.cmk_unified_search),
    )


def _creator(monkeypatch: pytest.MonkeyPatch, items: Iterable[object]) -> MainMenuConfigCreator:
    registry = MainMenuRegistry()
    for item in items:
        registry.register(item)  # type: ignore[arg-type]
    monkeypatch.setattr("cmk.gui.sidebar.main_menu.main_menu_registry", registry)
    return MainMenuConfigCreator(user_permissions=USER_PERMISSIONS, request=request)


def _page_context(config: Config) -> PageContext:
    return PageContext(config=config, request=request._get_current_object())


def test_a_menu_without_topics_and_without_a_vue_app_is_dropped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The Setup menu has topics only for permitted users; an empty menu must not render an
    entry that opens nothing."""
    with monkeypatch.context() as m:
        creator = _creator(
            m, [_search_item(), _item(NavItemIdEnum.setup, get_topics=lambda permissions: [])]
        )
        items = creator._get_menu_items(is_user_nav=False)

    assert [item.id for item in items] == [NavItemIdEnum.search]


def test_a_menu_that_hides_itself_is_dropped(monkeypatch: pytest.MonkeyPatch) -> None:
    with monkeypatch.context() as m:
        creator = _creator(
            m,
            [
                _search_item(),
                _item(
                    NavItemIdEnum.setup,
                    get_topics=lambda permissions: [_topic([_entry("a", "A")])],
                    hide=lambda: True,
                ),
            ],
        )
        items = creator._get_menu_items(is_user_nav=False)

    assert [item.id for item in items] == [NavItemIdEnum.search]


def test_a_link_item_becomes_a_nav_link_item(monkeypatch: pytest.MonkeyPatch) -> None:
    with monkeypatch.context() as m:
        creator = _creator(
            m,
            [
                _search_item(),
                MainMenuLinkItem(
                    id=NavItemIdEnum.help,
                    title=_l("Help"),
                    sort_index=1,
                    shortcut=NavItemShortcut(key="h"),
                    get_url=lambda req: "help.py",
                ),
            ],
        )
        items = creator._get_menu_items(is_user_nav=False)

    link_item = items[1]
    assert isinstance(link_item, NavLinkItem)
    assert link_item.url == "help.py"


def test_a_configurable_item_is_resolved_to_its_instance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A configurable menu decides per user whether it is a link or a menu with topics."""
    configurable = ConfigurableMainMenuItem(
        id=NavItemIdEnum.help,
        type=NavItemType.configurable,
        title=_l("Help"),
        sort_index=1,
        shortcut=NavItemShortcut(key="h"),
        get_item_instance=lambda item, usr: MainMenuLinkItem(
            id=NavItemIdEnum.help,
            title=_l("Help"),
            sort_index=1,
            shortcut=NavItemShortcut(key="h"),
            get_url=lambda req: "resolved.py",
        ),
    )
    with monkeypatch.context() as m:
        creator = _creator(m, [_search_item(), configurable])
        items = creator._get_menu_items(is_user_nav=False)

    link_item = items[1]
    assert isinstance(link_item, NavLinkItem)
    assert link_item.url == "resolved.py"


def test_a_link_item_with_only_a_static_url_loses_it(monkeypatch: pytest.MonkeyPatch) -> None:
    """Documents current behaviour: the URL is only taken over when the item also provides a
    ``get_url`` callback, so a link item configured with a plain ``url`` renders without one."""
    with monkeypatch.context() as m:
        creator = _creator(
            m,
            [
                _search_item(),
                MainMenuLinkItem(
                    id=NavItemIdEnum.help,
                    title=_l("Help"),
                    sort_index=1,
                    shortcut=NavItemShortcut(key="h"),
                    url="help.py",
                ),
            ],
        )
        items = creator._get_menu_items(is_user_nav=False)

    link_item = items[1]
    assert isinstance(link_item, NavLinkItem)
    assert link_item.url is None


def test_menu_items_are_split_between_the_main_and_the_user_navigation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with monkeypatch.context() as m:
        creator = _creator(
            m,
            [
                _search_item(),
                _item(
                    NavItemIdEnum.user,
                    is_user_nav=True,
                    get_topics=lambda permissions: [_topic([_entry("a", "A")])],
                ),
            ],
        )

        assert [item.id for item in creator._get_menu_items(is_user_nav=False)] == [
            NavItemIdEnum.search
        ]
        assert [item.id for item in creator._get_menu_items(is_user_nav=True)] == [
            NavItemIdEnum.user
        ]


def test_show_more_is_only_offered_when_a_topic_has_show_more_entries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plain = NavItemTopic(id="t", title="T", sort_index=0, entries=[_entry("a", "A")])
    with_show_more = NavItemTopic(
        id="t",
        title="T",
        sort_index=0,
        entries=[NavItemTopicEntry(id="a", title="A", sort_index=0, is_show_more=True)],
    )
    with monkeypatch.context() as m:
        creator = _creator(m, [_search_item()])

        without = creator._get_nav_item_from_main_menu_item(
            _item(NavItemIdEnum.setup, topics=[plain], header=NavItemHeader())
        )
        with_ = creator._get_nav_item_from_main_menu_item(
            _item(NavItemIdEnum.setup, topics=[with_show_more], header=NavItemHeader())
        )

    assert isinstance(without, NavItem)
    assert isinstance(with_, NavItem)
    assert without.show_more is None
    assert with_.show_more is not None


def test_entries_of_a_topic_are_sorted_by_sort_index(monkeypatch: pytest.MonkeyPatch) -> None:
    with monkeypatch.context() as m:
        creator = _creator(m, [_search_item()])
        entries = creator._get_entries_of_topic(
            _topic([_entry("b", "B", sort_index=2), _entry("a", "A", sort_index=1)])
        )

    assert [entry.id for entry in entries] == ["a", "b"]


def test_a_grouping_entry_keeps_its_children_and_loses_its_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An indented entry is a group heading, not a link - it must not become clickable."""
    with monkeypatch.context() as m:
        creator = _creator(m, [_search_item()])
        entries = creator._get_entries_of_topic(
            _topic(
                [
                    _entry(
                        "group",
                        "Group",
                        mode=TopicItemMode.indented,
                        entries=[_entry("a", "A")],
                    )
                ]
            )
        )

    assert entries[0].url is None
    assert entries[0].entries is not None
    assert [child.id for child in entries[0].entries] == ["a"]


def test_an_item_entry_keeps_its_url_and_has_no_children(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with monkeypatch.context() as m:
        creator = _creator(m, [_search_item()])
        entries = creator._get_entries_of_topic(_topic([_entry("a", "A")]))

    assert entries[0].url == "view.py"
    assert entries[0].mode == TopicItemMode.item
    assert entries[0].entries is None


def test_entries_of_a_topic_without_entries(monkeypatch: pytest.MonkeyPatch) -> None:
    with monkeypatch.context() as m:
        creator = _creator(m, [_search_item()])

        assert creator._get_entries_of_topic(_topic([])) == []


def test_topics_of_a_menu_without_topics(monkeypatch: pytest.MonkeyPatch) -> None:
    with monkeypatch.context() as m:
        creator = _creator(m, [_search_item()])

        assert creator._get_topics_of_menu(_item(NavItemIdEnum.setup)) == []


@pytest.mark.parametrize(
    "menu_id,expected_active",
    [
        pytest.param(NavItemIdEnum.monitoring, True, id="monitoring_is_searchable"),
        pytest.param(NavItemIdEnum.customize, True, id="customize_is_searchable"),
        pytest.param(NavItemIdEnum.setup, True, id="setup_is_searchable"),
        pytest.param(NavItemIdEnum.help, False, id="help_is_not_searchable"),
    ],
)
def test_only_the_searchable_menus_become_unified_search_providers(
    monkeypatch: pytest.MonkeyPatch, menu_id: NavItemIdEnum, expected_active: bool
) -> None:
    with monkeypatch.context() as m:
        creator = _creator(m, [_search_item()])
        before = creator.search_config.providers
        creator._add_unified_searchprovider(_item(menu_id))
        after = creator.search_config.providers

    if expected_active:
        assert getattr(after, menu_id.value).active is True
    else:
        assert after == before


def test_create_injects_the_search_config_into_the_search_menu(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The search providers are only known after every menu has been collected, so the
    search menu's Vue app has to be filled in afterwards."""
    with monkeypatch.context() as m:
        creator = _creator(
            m,
            [
                _search_item(),
                _item(
                    NavItemIdEnum.monitoring,
                    sort_index=5,
                    get_topics=lambda permissions: [_topic([_entry("a", "A")])],
                ),
            ],
        )
        config = creator.create(start_url="index.py", home_icon_path=None)

    search_item = next(item for item in config.main if item.id == NavItemIdEnum.search)
    assert isinstance(search_item, NavItem)
    assert search_item.vue_app is not None
    assert search_item.vue_app.data is not None
    assert search_item.vue_app.data["providers"]["monitoring"]["active"] is True


def test_create_prefers_the_users_own_start_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """A user who configured a start page must land there, not on the site default."""
    with monkeypatch.context() as m:
        creator = _creator(m, [_search_item()])
        config = creator.create(start_url="index.py", home_icon_path="logo.svg")

    assert config.start.url == (user.start_url or "index.py")
    assert config.start.icon_path == "logo.svg"


def test_message_read_confirms_the_deletion(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    deleted: list[str] = []
    request.set_var("id", "abc")
    with monkeypatch.context() as m:
        m.setattr(message, "delete_gui_message", deleted.append)
        with output_funnel.plugged():
            ajax_message_read(_page_context(load_config))
            assert output_funnel.drain() == "OK"

    assert deleted == ["abc"]


def test_message_read_reports_a_failure_as_text(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    """The endpoint is polled by the sidebar; a stack trace in the response would break the
    poll loop, so failures are reduced to a marker."""
    request.set_var("id", "abc")
    with monkeypatch.context() as m:
        m.setattr(
            message,
            "delete_gui_message",
            lambda _id: (_ for _ in ()).throw(ValueError("gone")),
        )
        with output_funnel.plugged():
            ajax_message_read(_page_context(load_config))
            assert output_funnel.drain() == "ERROR"


def test_message_read_reraises_in_debug_mode(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    request.set_var("id", "abc")
    with monkeypatch.context() as m:
        m.setattr(
            message,
            "delete_gui_message",
            lambda _id: (_ for _ in ()).throw(ValueError("gone")),
        )
        with pytest.raises(ValueError, match="gone"):
            ajax_message_read(_page_context(dataclasses.replace(load_config, debug=True)))


def test_get_messages_separates_popups_from_hints(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    messages = [
        {"id": "1", "methods": ["gui_popup"], "text": {"content": "Popup"}},
        {"id": "2", "methods": ["gui_hint"], "text": {"content": "Hint"}},
        {"id": "3", "methods": ["gui_hint"], "text": {"content": "Read"}, "acknowledged": True},
    ]
    with monkeypatch.context() as m:
        m.setattr(message, "get_gui_messages", lambda: messages)
        result = PageAjaxSidebarGetMessages().page(_page_context(load_config))

    assert isinstance(result, dict)
    assert result["popup_messages"] == [{"id": "1", "text": "Popup"}]
    assert result["hint_messages"]["count"] == 1


def test_unack_werks_needs_the_acknowledge_permission(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    with monkeypatch.context() as m:
        m.setattr("cmk.gui.sidebar.main_menu.may_acknowledge", lambda: False)
        with pytest.raises(MKAuthException):
            PageAjaxSidebarGetUnackIncompWerks().page(_page_context(load_config))


@pytest.mark.parametrize(
    "count,expected_tooltip",
    [
        pytest.param(1, "1 unacknowledged incompatible werk", id="singular"),
        pytest.param(3, "3 unacknowledged incompatible werks", id="plural"),
        pytest.param(0, "0 unacknowledged incompatible werks", id="zero_is_plural"),
    ],
)
def test_unack_werks_tooltip_is_pluralized(
    monkeypatch: pytest.MonkeyPatch, load_config: Config, count: int, expected_tooltip: str
) -> None:
    with monkeypatch.context() as m:
        m.setattr("cmk.gui.sidebar.main_menu.may_acknowledge", lambda: True)
        m.setattr("cmk.gui.sidebar.main_menu.num_unacknowledged_incompatible_werks", lambda: count)
        result = PageAjaxSidebarGetUnackIncompWerks().page(_page_context(load_config))

    assert isinstance(result, dict)
    assert result["count"] == count
    assert result["tooltip"] == expected_tooltip


def test_sites_and_changes_rejects_a_non_uuid_activation_id(load_config: Config) -> None:
    """The activation id is used to build file paths, so anything but a UUID has to be
    refused before it reaches the filesystem."""
    request.set_var("activation_id", "../../etc/passwd")

    with pytest.raises(MKUserError, match="Invalid activation_id"):
        PageAjaxSitesAndChanges().page(_page_context(load_config))


def test_sites_and_changes_accepts_a_uuid_activation_id(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    recorder = _PopoutRecorder()
    request.set_var("activation_id", "6f4f0e0e-3f4c-4a1a-9c4f-0d1e2f3a4b5c")
    with monkeypatch.context() as m:
        m.setattr(
            "cmk.gui.watolib.activate_changes.ActivateChanges."
            "get_all_data_required_for_activation_popout",
            recorder,
        )
        PageAjaxSitesAndChanges().page(_page_context(load_config))

    assert recorder.activation_ids == ["6f4f0e0e-3f4c-4a1a-9c4f-0d1e2f3a4b5c"]


def test_sites_and_changes_without_an_activation_id(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    recorder = _PopoutRecorder()
    with monkeypatch.context() as m:
        m.setattr(
            "cmk.gui.watolib.activate_changes.ActivateChanges."
            "get_all_data_required_for_activation_popout",
            recorder,
        )
        PageAjaxSitesAndChanges().page(_page_context(load_config))

    assert recorder.activation_ids == [None]


@dataclasses.dataclass
class _EmptyPopout:
    """Stands in for the activation popout payload, which is only asdict()-ed here."""


class _PopoutRecorder:
    """Records which activation id reached the activation layer."""

    def __init__(self) -> None:
        self.activation_ids: list[str | None] = []

    def __call__(self, _sites: object, activation_id: str | None) -> _EmptyPopout:
        self.activation_ids.append(activation_id)
        return _EmptyPopout()
