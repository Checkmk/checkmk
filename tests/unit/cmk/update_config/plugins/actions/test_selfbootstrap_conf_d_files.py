#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest

from cmk.gui.watolib.password_store import PasswordStore
from cmk.gui.watolib.utils import multisite_dir
from cmk.update_config.plugins.actions.selfbootstrap_conf_d_files import (
    COMMUNITY_EXTEND_ONLY_FILES,
)
from cmk.update_config.plugins.lib.selfbootstrap_conf_d_files import resave_extend_only_files
from cmk.utils import password_store
from tests.unit.cmk.update_config.plugins.actions.selfbootstrap_conf_d_helpers import (
    load_unseeded,
    make_wato_dir,
)

_LOGGER = logging.getLogger(__name__)


@pytest.fixture(name="wato_dir")
def wato_dir_fixture() -> Iterator[Path]:
    gui_dir = multisite_dir()
    # We can't assume it does not exist: plugin registration at session start creates it
    # (cmk.bi.filesystem). It must be empty, though.
    gui_dir.mkdir(parents=True, exist_ok=True)
    assert not any(gui_dir.iterdir())
    try:
        yield from make_wato_dir()
    finally:
        shutil.rmtree(gui_dir)
        password_store.password_store_path().unlink(missing_ok=True)


def _resave_all(logger: logging.Logger = _LOGGER) -> None:
    resave_extend_only_files(COMMUNITY_EXTEND_ONLY_FILES, pprint_value=False, logger=logger)


@pytest.mark.parametrize(
    "file_name, variable, value",
    [
        pytest.param("contacts.mk", "contacts", {"admin": {"alias": "Admin"}}, id="contacts"),
        pytest.param(
            "notifications.mk",
            "notification_rules",
            [{"description": "r1", "notify_plugin": ("mail", None)}],
            id="notification rules",
        ),
        pytest.param(
            "timeperiods.mk",
            "timeperiods",
            {"workhours": {"alias": "Work", "monday": [("08:00", "17:00")]}},
            id="time periods",
        ),
        pytest.param(
            "predefined_conditions.mk",
            "predefined_conditions",
            {"c1": {"title": "C1", "conditions": {}, "owned_by": None, "shared_with": []}},
            id="predefined conditions",
        ),
        pytest.param(
            "oauth2_connections.mk",
            "oauth2_connections",
            {"o1": {"title": "O1", "client_id": "x"}},
            id="oauth2 connections",
        ),
    ],
)
def test_rewrites_a_file_written_by_an_earlier_version(
    wato_dir: Path, file_name: str, variable: str, value: object
) -> None:
    path = wato_dir / file_name
    path.write_text(f"# Written by Checkmk store\n\n{variable}{_extend(value)}\n")

    _resave_all()

    assert load_unseeded(path) == {variable: value}


def _extend(value: object) -> str:
    return f" += {value!r}" if isinstance(value, list) else f".update({value!r})"


def test_notification_parameters_keep_their_order(wato_dir: Path) -> None:
    path = wato_dir / "notification_parameter.mk"
    path.write_text("notification_parameter.update({'mail': {'b': {}, 'a': {}}})\n")

    resave_extend_only_files(COMMUNITY_EXTEND_ONLY_FILES, pprint_value=True, logger=_LOGGER)

    parameters = load_unseeded(path)["notification_parameter"]
    assert isinstance(parameters, dict)
    assert list(parameters["mail"]) == ["b", "a"]


def test_rewrites_the_passwords_file_and_keeps_the_secret(wato_dir: Path) -> None:
    path = wato_dir / "passwords.mk"
    # The secret itself lives in the password store; the file carries an empty placeholder
    meta: dict[str, dict[str, object]] = {
        "pw1": {
            "title": "PW",
            "comment": "",
            "docu_url": "",
            "owned_by": None,
            "shared_with": [],
            "password": "",
        }
    }
    path.write_text(f"stored_passwords.update({meta!r})\n")
    password_store.save({"pw1": "secret"}, password_store.password_store_path())

    _resave_all()

    assert load_unseeded(path) == {"stored_passwords": meta}
    assert PasswordStore().load_for_reading()["pw1"]["password"] == "secret"


def test_rewrites_the_group_aliases_written_by_2_3(wato_dir: Path) -> None:
    path = wato_dir / "groups.mk"
    path.write_text(
        "if type(define_hostgroups) != dict:\n"
        "    define_hostgroups = {}\n"
        "define_hostgroups.update({'linux': 'Linux servers'})\n\n"
        "if type(define_contactgroups) != dict:\n"
        "    define_contactgroups = {}\n"
        "define_contactgroups.update({'all': 'Everything'})\n\n"
    )

    _resave_all()

    assert load_unseeded(path) == {
        "define_hostgroups": {"linux": "Linux servers"},
        "define_servicegroups": {},
        "define_contactgroups": {"all": "Everything"},
    }


def test_leaves_the_group_aliases_alone_if_they_are_assigned(wato_dir: Path) -> None:
    path = wato_dir / "groups.mk"
    content = (
        "define_hostgroups = {'linux': 'Linux servers'}\n"
        "define_servicegroups = {}\n"
        "define_contactgroups = {}\n"
    )
    path.write_text(content)

    _resave_all()

    assert path.read_text() == content


def test_rewrites_the_base_tags_file_from_the_gui_one(wato_dir: Path) -> None:
    tag_config = {"aux_tags": [], "tag_groups": [{"id": "g", "title": "G", "tags": []}]}
    (multisite_dir() / "tags.mk").write_text(f"wato_tags.update({tag_config!r})\n")
    (wato_dir / "tags.mk").write_text(f"tag_config.update({tag_config!r})\n")

    _resave_all()

    assert load_unseeded(wato_dir / "tags.mk") == {"tag_config": tag_config}


def test_leaves_the_base_tags_file_alone_without_the_gui_one(
    wato_dir: Path, caplog: pytest.LogCaptureFixture
) -> None:
    path = wato_dir / "tags.mk"
    content = "tag_config.update({'aux_tags': [], 'tag_groups': []})\n"
    path.write_text(content)

    _resave_all()

    assert path.read_text() == content
    assert [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING] == [
        (
            f"{path}: left unchanged, it cannot be re-saved: "
            f"{multisite_dir() / 'tags.mk'} is missing, cannot regenerate the base tags file"
        )
    ]
