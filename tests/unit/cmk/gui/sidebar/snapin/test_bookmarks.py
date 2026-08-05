#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator

import pytest

import cmk.utils.paths
from cmk.ccc import store
from cmk.ccc.user import UserId
from cmk.gui import pagetypes
from cmk.gui.config import Config
from cmk.gui.exceptions import MKUserError
from cmk.gui.logged_in import user
from cmk.gui.sidebar._snapin._bookmarks import (
    BookmarkList,
    BookmarkListConfig,
    Bookmarks,
    BookmarkSpec,
)
from cmk.gui.type_defs import DynamicIconName
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.roles import UserPermissions

USER_PERMISSIONS = UserPermissions({}, {}, {}, [])


class FakeRequest:
    def __init__(self, referer: str | None) -> None:
        self.referer = referer


def _bookmark(title: str, url: str, *, topic: str | None = None) -> BookmarkSpec:
    return {"title": title, "url": url, "icon": None, "topic": topic}


def _bookmark_list(
    name: str,
    owner: UserId,
    *,
    default_topic: str = "My Bookmarks",
    bookmarks: list[BookmarkSpec] | None = None,
) -> BookmarkList:
    return BookmarkList(
        BookmarkListConfig(
            name=name,
            title=name,
            description="",
            owner=owner,
            public=False,
            hidden=False,
            default_topic=default_topic,
            bookmarks=bookmarks if bookmarks is not None else [],
        )
    )


def _write_user_bookmark_lists(user_id: UserId, spec: dict[str, object]) -> None:
    profile_dir = cmk.utils.paths.profile_dir / user_id
    profile_dir.mkdir(parents=True, exist_ok=True)
    store.save_object_to_file(profile_dir / "user_bookmark_lists.mk", spec)


@pytest.fixture(name="permissive_user", autouse=True)
def fixture_permissive_user(
    request_context: None, monkeypatch: pytest.MonkeyPatch
) -> Iterator[None]:
    with monkeypatch.context() as m:
        m.setattr(user, "may", lambda x: True)
        yield


def test_type_name_and_phrases() -> None:
    assert BookmarkList.type_name() == "bookmark_list"
    assert BookmarkList.phrase("title") == "Bookmark list"
    assert BookmarkList.phrase("new") == "Add list"


def test_serialize_deserialize_roundtrip() -> None:
    original = _bookmark_list(
        "my_bookmarks",
        UserId("harry"),
        default_topic="Mine",
        bookmarks=[_bookmark("All hosts", "view.py?view_name=allhosts", topic="Hosts")],
    )

    restored = BookmarkList.deserialize(original.serialize())

    assert restored.config == original.config


def test_new_bookmark_defaults_to_the_lists_topic_and_icon() -> None:
    assert BookmarkList.new_bookmark("All hosts", "view.py") == {
        "title": "All hosts",
        "url": "view.py",
        "icon": None,
        "topic": None,
    }


def test_add_bookmark_appends_to_the_list() -> None:
    bookmark_list = _bookmark_list("my_bookmarks", UserId("harry"))

    bookmark_list.add_bookmark("All hosts", "view.py?view_name=allhosts")

    assert bookmark_list.config.bookmarks == [_bookmark("All hosts", "view.py?view_name=allhosts")]


def test_bookmarks_by_topic_uses_the_default_topic_as_fallback() -> None:
    bookmark_list = _bookmark_list(
        "my_bookmarks",
        UserId("harry"),
        default_topic="Mine",
        bookmarks=[
            _bookmark("A", "a.py"),
            _bookmark("B", "b.py", topic="Hosts"),
            _bookmark("C", "c.py"),
        ],
    )

    assert [
        (topic, [b["title"] for b in bookmarks])
        for topic, bookmarks in bookmark_list.bookmarks_by_topic()
    ] == [("Hosts", ["B"]), ("Mine", ["A", "C"])]


def test_bookmarks_by_topic_of_an_empty_list() -> None:
    assert _bookmark_list("my_bookmarks", UserId("harry")).bookmarks_by_topic() == []


def test_default_bookmark_topic() -> None:
    assert (
        _bookmark_list(
            "my_bookmarks", UserId("harry"), default_topic="Mine"
        ).default_bookmark_topic()
        == "Mine"
    )


@pytest.mark.parametrize(
    "url",
    [
        pytest.param("http://example.com/x", id="http"),
        pytest.param("https://example.com/x", id="https"),
        pytest.param("view.py?view_name=allhosts", id="relative"),
    ],
)
def test_validate_url_accepts_web_urls(url: str) -> None:
    assert BookmarkList.validate_url(url, "url") is None


@pytest.mark.parametrize(
    "url",
    [
        pytest.param("javascript:alert(1)", id="javascript"),
        pytest.param("data:text/html,<script>alert(1)</script>", id="data"),
    ],
)
def test_validate_url_rejects_script_schemes(url: str) -> None:
    """A bookmark URL ends up in an ``href``, so anything that can execute must be refused
    at configuration time."""
    with pytest.raises(MKUserError):
        BookmarkList.validate_url(url, "url")


def test_add_default_bookmark_list_creates_the_personal_list() -> None:
    instances: pagetypes.OverridableInstances[BookmarkList] = pagetypes.OverridableInstances()

    BookmarkList.add_default_bookmark_list(instances, UserId("harry"))

    assert instances.has_instance((UserId("harry"), "my_bookmarks"))
    created = instances.instance((UserId("harry"), "my_bookmarks"))
    assert created.default_bookmark_topic() == "My Bookmarks"
    assert created.config.bookmarks == []
    assert created.config.public is False


def test_topic_choices_are_sorted_and_deduplicated(with_user_login: UserId) -> None:
    user_id = with_user_login
    _write_user_bookmark_lists(
        user_id,
        {
            "my_bookmarks": {
                "title": "My Bookmarks",
                "description": "",
                "public": False,
                "default_topic": "Mine",
                "bookmarks": [
                    _bookmark("A", "a.py", topic="Zebra"),
                    _bookmark("B", "b.py", topic="Apple"),
                    _bookmark("C", "c.py", topic="Apple"),
                    _bookmark("D", "d.py"),
                ],
            }
        },
    )

    assert BookmarkList._topic_choices(USER_PERMISSIONS) == [
        ("Apple", "Apple"),
        ("Mine", "Mine"),
        ("Zebra", "Zebra"),
    ]


def test_snapin_metadata() -> None:
    assert Bookmarks.type_name() == "bookmarks"
    assert Bookmarks.title() == "Bookmarks"
    assert "bookmarks" in Bookmarks.description()


def test_page_handlers_expose_the_add_endpoint() -> None:
    assert list(Bookmarks().page_handlers()) == ["add_bookmark"]


def test_get_bookmarks_by_topic_merges_all_permitted_lists(with_user_login: UserId) -> None:
    user_id = with_user_login
    _write_user_bookmark_lists(
        user_id,
        {
            "first": {
                "title": "First",
                "description": "",
                "public": False,
                "default_topic": "Shared",
                "bookmarks": [_bookmark("A", "a.py")],
            },
            "second": {
                "title": "Second",
                "description": "",
                "public": False,
                "default_topic": "Shared",
                "bookmarks": [_bookmark("B", "b.py")],
            },
        },
    )

    assert [
        (topic, [b["title"] for b in bookmarks])
        for topic, bookmarks in Bookmarks()._get_bookmarks_by_topic(USER_PERMISSIONS)
    ] == [("Shared", ["A", "B"])]


@pytest.mark.usefixtures("patch_theme")
def test_show_renders_a_foldable_topic_per_bookmark_topic(
    with_user_login: UserId, load_config: Config
) -> None:
    user_id = with_user_login
    _write_user_bookmark_lists(
        user_id,
        {
            "my_bookmarks": {
                "title": "My Bookmarks",
                "description": "",
                "public": False,
                "default_topic": "Mine",
                "bookmarks": [
                    _bookmark("All hosts", "view.py?view_name=allhosts"),
                    _bookmark("Icons", "view.py", topic="Other"),
                ],
            }
        },
    )

    with output_funnel.plugged():
        Bookmarks().show(load_config)
        rendered = output_funnel.drain()

    assert "Mine" in rendered
    assert "Other" in rendered
    assert "All hosts" in rendered
    assert "cmk.sidebar.add_bookmark()" in rendered
    assert "bookmark_lists.py" in rendered


@pytest.mark.usefixtures("patch_theme")
def test_show_falls_back_to_the_bookmark_list_icon(
    with_user_login: UserId, load_config: Config
) -> None:
    """A bookmark without its own icon must still render a link, not an empty anchor."""
    user_id = with_user_login
    _write_user_bookmark_lists(
        user_id,
        {
            "my_bookmarks": {
                "title": "My Bookmarks",
                "description": "",
                "public": False,
                "default_topic": "Mine",
                "bookmarks": [
                    {
                        "title": "With icon",
                        "url": "view.py",
                        "icon": DynamicIconName("host"),
                        "topic": None,
                    },
                    _bookmark("Without icon", "view.py?view_name=allhosts"),
                ],
            }
        },
    )

    with output_funnel.plugged():
        Bookmarks().show(load_config)
        rendered = output_funnel.drain()

    assert "With icon" in rendered
    assert "Without icon" in rendered


def test_add_bookmark_creates_the_personal_list_on_demand(
    with_user_login: UserId, load_config: Config
) -> None:
    Bookmarks()._add_bookmark("All hosts", "view.py?view_name=allhosts", USER_PERMISSIONS)

    instances = BookmarkList.load(USER_PERMISSIONS)
    stored = instances.instance((with_user_login, "my_bookmarks"))
    assert [b["title"] for b in stored.config.bookmarks] == ["All hosts"]


def test_add_bookmark_appends_to_an_existing_personal_list(
    with_user_login: UserId, load_config: Config
) -> None:
    _write_user_bookmark_lists(
        with_user_login,
        {
            "my_bookmarks": {
                "title": "My Bookmarks",
                "description": "",
                "public": False,
                "default_topic": "Mine",
                "bookmarks": [_bookmark("First", "a.py")],
            }
        },
    )

    Bookmarks()._add_bookmark("Second", "b.py", USER_PERMISSIONS)

    stored = BookmarkList.load(USER_PERMISSIONS).instance((with_user_login, "my_bookmarks"))
    assert [b["title"] for b in stored.config.bookmarks] == ["First", "Second"]


@pytest.mark.parametrize(
    "referer,url,expected",
    [
        pytest.param(
            None,
            "http://host/NO_SITE/check_mk/view.py",
            "http://host/NO_SITE/check_mk/view.py",
            id="without_a_referer_nothing_can_be_stripped",
        ),
        pytest.param(
            "https://host/NO_SITE/check_mk/sidebar.py",
            "http://host/NO_SITE/check_mk/view.py",
            "http://host/NO_SITE/check_mk/view.py",
            id="different_scheme_keeps_the_full_url",
        ),
        pytest.param(
            "http://other/NO_SITE/check_mk/sidebar.py",
            "http://host/NO_SITE/check_mk/view.py",
            "http://host/NO_SITE/check_mk/view.py",
            id="different_host_keeps_the_full_url",
        ),
        pytest.param(
            "http://host/NO_SITE/check_mk/sidebar.py",
            "http://host/NO_SITE/check_mk/view.py?view_name=allhosts",
            "view.py?view_name=allhosts",
            id="same_directory_becomes_relative_and_keeps_the_query",
        ),
        pytest.param(
            "http://host/NO_SITE/check_mk/sidebar.py",
            "http://host/NO_SITE/check_mk/view.py",
            "view.py",
            id="same_directory_without_a_query",
        ),
        pytest.param(
            "http://host/sidebar.py",
            "http://host/view.py",
            "/view.py",
            id="document_root_stays_absolute",
        ),
        pytest.param(
            "http://host/NO_SITE/check_mk/sidebar.py",
            "http://host/NO_SITE/pnp4nagios/index.php",
            "../pnp4nagios/index.php",
            id="sibling_directory_becomes_relative_to_the_sidebar",
        ),
    ],
)
def test_try_shorten_url(
    monkeypatch: pytest.MonkeyPatch, referer: str | None, url: str, expected: str
) -> None:
    """Bookmarks are stored in the user's config file, so they must not pin the host name
    the bookmark happened to be created on."""
    monkeypatch.setattr("cmk.gui.sidebar._snapin._bookmarks.request", FakeRequest(referer=referer))

    assert Bookmarks()._try_shorten_url(url) == expected
