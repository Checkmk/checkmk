#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Sequence
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from cmk.gui import sidebar
from cmk.gui.config import active_config, Config
from cmk.gui.http import request
from cmk.gui.logged_in import user
from cmk.gui.sidebar import UserSidebarSnapin


@pytest.fixture(scope="function", autouse=True)
def fixture_user(request_context: None, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    with monkeypatch.context() as m:
        m.setattr(user, "confdir", Path(""))
        m.setattr(user, "may", lambda x: True)
        yield


def test_user_config_fold_unfold() -> None:
    user_config = sidebar.UserSidebarConfig(user, active_config.sidebar)
    assert user_config.folded is False
    user_config.folded = True
    assert user_config.folded is True
    user_config.folded = False
    assert user_config.folded is False


def test_user_config_add_snapin() -> None:
    user_config = sidebar.UserSidebarConfig(user, active_config.sidebar)
    del user_config.snapins[:]
    snapin = UserSidebarSnapin.from_snapin_type_id("tactical_overview")
    user_config.add_snapin(snapin)
    assert user_config.snapins == [snapin]


def test_user_config_get_snapin() -> None:
    user_config = sidebar.UserSidebarConfig(user, active_config.sidebar)
    del user_config.snapins[:]
    snapin = UserSidebarSnapin.from_snapin_type_id("tactical_overview")
    user_config.add_snapin(snapin)

    assert user_config.get_snapin("tactical_overview") == snapin


def test_user_config_get_not_existing_snapin() -> None:
    user_config = sidebar.UserSidebarConfig(user, active_config.sidebar)
    del user_config.snapins[:]

    with pytest.raises(KeyError) as e:
        user_config.get_snapin("tactical_overview")
    msg = "%s" % e
    assert "does not exist" in msg


@pytest.mark.parametrize(
    "move_id,before_id,result",
    [
        (
            "tactical_overview",
            "views",
            ["performance", "tactical_overview", "views"],
        ),
        (
            "tactical_overview",
            "performance",
            ["tactical_overview", "performance", "views"],
        ),
        ("not_existing", "performance", None),
        # TODO: Shouldn't this also be handled?
        # ("performance",  "not_existing", [
        #    ("performance", "open"),
        #    ("views", "open"),
        #    ("tactical_overview", "open"),
        # ]),
        (
            "performance",
            "",
            ["views", "tactical_overview", "performance"],
        ),
    ],
)
def test_user_config_move_snapin_before(
    move_id: str, before_id: str, result: Sequence[str]
) -> None:
    user_config = sidebar.UserSidebarConfig(user, active_config.sidebar)
    del user_config.snapins[:]
    user_config.snapins.extend(
        [
            UserSidebarSnapin.from_snapin_type_id("performance"),
            UserSidebarSnapin.from_snapin_type_id("views"),
            UserSidebarSnapin.from_snapin_type_id("tactical_overview"),
        ]
    )

    try:
        move = user_config.get_snapin(move_id)
    except KeyError as e:
        if result is None:
            assert "does not exist" in "%s" % e
            return
        raise

    try:
        before: UserSidebarSnapin | None = user_config.get_snapin(before_id)
    except KeyError:
        before = None

    user_config.move_snapin_before(move, before)
    assert user_config.snapins == [
        UserSidebarSnapin.from_snapin_type_id(snapin_id) for snapin_id in result
    ]


def test_load_default_config() -> None:
    user_config = sidebar.UserSidebarConfig(user, active_config.sidebar)
    assert user_config.folded is False
    assert user_config.snapins == [
        UserSidebarSnapin.from_snapin_type_id("tactical_overview"),
        UserSidebarSnapin.from_snapin_type_id("bookmarks"),
        UserSidebarSnapin(
            sidebar.snapin_registry["master_control"], sidebar.SnapinVisibility.CLOSED
        ),
    ]


def test_load_legacy_list_user_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        sidebar.UserSidebarConfig,
        "_user_config",
        lambda x: [("tactical_overview", "open"), ("views", "closed")],
    )

    user_config = sidebar.UserSidebarConfig(user, active_config.sidebar)
    assert user_config.folded is False
    assert user_config.snapins == [
        UserSidebarSnapin.from_snapin_type_id("tactical_overview"),
        UserSidebarSnapin(sidebar.snapin_registry["views"], sidebar.SnapinVisibility.CLOSED),
    ]


def test_load_legacy_off_user_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        sidebar.UserSidebarConfig,
        "_user_config",
        lambda x: [("search", "off"), ("views", "closed")],
    )

    user_config = sidebar.UserSidebarConfig(user, active_config.sidebar)
    assert user_config.folded is False
    assert user_config.snapins == [
        UserSidebarSnapin(sidebar.snapin_registry["views"], sidebar.SnapinVisibility.CLOSED),
    ]


def test_load_skip_not_existing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        sidebar.UserSidebarConfig,
        "_user_config",
        lambda x: {"fold": False, "snapins": [("bla", "closed"), ("views", "closed")]},
    )

    user_config = sidebar.UserSidebarConfig(user, active_config.sidebar)
    assert user_config.folded is False
    assert user_config.snapins == [
        UserSidebarSnapin(sidebar.snapin_registry["views"], sidebar.SnapinVisibility.CLOSED),
    ]


def test_load_skip_not_permitted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        sidebar.UserSidebarConfig,
        "_user_config",
        lambda x: {
            "fold": False,
            "snapins": [("tactical_overview", "closed"), ("views", "closed")],
        },
    )
    with monkeypatch.context() as m:
        m.setattr(user, "may", lambda x: x != "sidesnap.tactical_overview")

        user_config = sidebar.UserSidebarConfig(user, active_config.sidebar)
        assert user_config.folded is False
        assert user_config.snapins == [
            UserSidebarSnapin(sidebar.snapin_registry["views"], sidebar.SnapinVisibility.CLOSED),
        ]


def test_load_user_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        sidebar.UserSidebarConfig,
        "_user_config",
        lambda x: {
            "fold": True,
            "snapins": [
                ("search", "closed"),
                ("views", "open"),
            ],
        },
    )

    user_config = sidebar.UserSidebarConfig(user, active_config.sidebar)
    assert user_config.folded is True
    assert user_config.snapins == [
        UserSidebarSnapin(sidebar.snapin_registry["search"], sidebar.SnapinVisibility.CLOSED),
        UserSidebarSnapin.from_snapin_type_id("views"),
    ]


def test_save_user_config_denied(mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch) -> None:
    with monkeypatch.context() as m:
        m.setattr(user, "may", lambda x: x != "general.configure_sidebar")
        save_user_file_mock = mocker.patch.object(user, "save_file")
        user_config = sidebar.UserSidebarConfig(user, active_config.sidebar)
        user_config.save()
        save_user_file_mock.assert_not_called()
        mocker.stopall()


def test_save_user_config_allowed(mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch) -> None:
    with monkeypatch.context() as m:
        m.setattr(user, "may", lambda x: x == "general.configure_sidebar")
        save_user_file_mock = mocker.patch.object(user, "save_file")
        user_config = sidebar.UserSidebarConfig(user, active_config.sidebar)
        user_config._config = {"fold": True, "snapins": []}
        user_config.save()
        save_user_file_mock.assert_called_once_with("sidebar", {"fold": True, "snapins": []})
        mocker.stopall()


@pytest.mark.parametrize(
    "origin_state,fold_var,set_state",
    [
        (False, "yes", True),
        (True, "", False),
    ],
)
def test_ajax_fold(
    mocker: MockerFixture, origin_state: bool, fold_var: str, set_state: bool
) -> None:
    m_config = mocker.patch.object(
        user,
        "load_file",
        return_value={
            "fold": origin_state,
            "snapins": [("tactical_overview", "open")],
        },
    )
    m_save = mocker.patch.object(user, "save_file")

    request.set_var("fold", fold_var)
    sidebar.AjaxFoldSnapin().page(Config())

    m_config.assert_called_once()
    m_save.assert_called_once_with(
        "sidebar",
        {
            "fold": set_state,
            "snapins": [
                {
                    "snapin_type_id": "tactical_overview",
                    "visibility": "open",
                }
            ],
        },
    )
    mocker.stopall()


@pytest.mark.parametrize(
    "origin_state,set_state",
    [
        ("open", "closed"),
        ("closed", "open"),
        ("closed", "closed"),
        ("open", "open"),
        ("open", "off"),
        ("closed", "off"),
    ],
)
def test_ajax_openclose_close(mocker: MockerFixture, origin_state: str, set_state: str) -> None:
    request.set_var("name", "tactical_overview")
    request.set_var("state", set_state)
    m_config = mocker.patch.object(
        user,
        "load_file",
        return_value={
            "fold": False,
            "snapins": [
                ("tactical_overview", origin_state),
                ("views", "open"),
            ],
        },
    )
    m_save = mocker.patch.object(user, "save_file")

    sidebar.AjaxOpenCloseSnapin().page(Config())

    snapins = [
        UserSidebarSnapin.from_snapin_type_id("views"),
    ]

    if set_state != "off":
        snapins.insert(
            0,
            UserSidebarSnapin.from_config(
                {"snapin_type_id": "tactical_overview", "visibility": set_state}
            ),
        )

    m_config.assert_called_once()
    m_save.assert_called_once_with(
        "sidebar",
        {
            "fold": False,
            "snapins": [e.to_config() for e in snapins],
        },
    )
    mocker.stopall()


def test_move_snapin_not_permitted(monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture) -> None:
    with monkeypatch.context() as m:
        m.setattr(user, "may", lambda x: x != "general.configure_sidebar")
        m_load = mocker.patch.object(sidebar.UserSidebarConfig, "_load")
        sidebar.move_snapin(Config())
        m_load.assert_not_called()


@pytest.mark.parametrize(
    "move,before,do_save",
    [
        ("tactical_overview", "views", True),
        ("not_existing", "performance", None),
    ],
)
def test_move_snapin(mocker: MockerFixture, move: str, before: str, do_save: bool) -> None:
    request.set_var("name", move)
    request.set_var("before", before)
    m_save = mocker.patch.object(sidebar.UserSidebarConfig, "save")

    sidebar.move_snapin(Config())

    if do_save is None:
        m_save.assert_not_called()
    else:
        m_save.assert_called_once()
