#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import os

import pytest

import omdlib.main
from omdlib.type_defs import Skeleton


def test_hostname() -> None:
    assert omdlib.main.hostname() == os.popen("hostname").read().strip()


def test_permission_action_new_link_triggers_no_action() -> None:
    assert (
        omdlib.main.permission_action(
            site_home="/tmp",
            conflict_mode=Skeleton.ASK,
            relpath="my/file",
            old_type="link",
            new_type="link",
            user_type="link",
            old_perm=123,
            new_perm=125,
            user_perm=124,
        )
        is None
    )
    assert (
        omdlib.main.permission_action(
            site_home="/tmp",
            conflict_mode=Skeleton.ASK,
            relpath="my/file",
            old_type="file",
            new_type="link",
            user_type="file",
            old_perm=123,
            new_perm=125,
            user_perm=124,
        )
        is None
    )
    assert (
        omdlib.main.permission_action(
            site_home="/tmp",
            conflict_mode=Skeleton.ASK,
            relpath="my/file",
            old_type="link",
            new_type="file",
            user_type="link",
            old_perm=123,
            new_perm=125,
            user_perm=124,
        )
        is None
    )


def test_permission_action_changed_type_triggers_no_action() -> None:
    assert (
        omdlib.main.permission_action(
            site_home="/tmp",
            conflict_mode=Skeleton.ASK,
            relpath="my/file",
            old_type="dir",
            new_type="file",
            user_type="dir",
            old_perm=123,
            new_perm=125,
            user_perm=124,
        )
        is None
    )
    assert (
        omdlib.main.permission_action(
            site_home="/tmp",
            conflict_mode=Skeleton.ASK,
            relpath="my/file",
            old_type="file",
            new_type="dir",
            user_type="file",
            old_perm=123,
            new_perm=125,
            user_perm=124,
        )
        is None
    )


def test_permission_action_same_target_permission_triggers_no_action() -> None:
    assert (
        omdlib.main.permission_action(
            site_home="/tmp",
            conflict_mode=Skeleton.ASK,
            relpath="my/file",
            old_type="file",
            new_type="file",
            user_type="file",
            old_perm=123,
            new_perm=125,
            user_perm=125,
        )
        is None
    )
    assert (
        omdlib.main.permission_action(
            site_home="/tmp",
            conflict_mode=Skeleton.ASK,
            relpath="my/file",
            old_type="dir",
            new_type="dir",
            user_type="dir",
            old_perm=123,
            new_perm=125,
            user_perm=125,
        )
        is None
    )


def test_permission_action_user_and_new_changed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(omdlib.main, "user_confirms", lambda *a: True)  # noqa: ARG005
    assert (
        omdlib.main.permission_action(
            site_home="/tmp",
            conflict_mode=Skeleton.ASK,
            relpath="my/file",
            old_type="file",
            new_type="file",
            user_type="file",
            old_perm=123,
            new_perm=124,
            user_perm=125,
        )
        == "keep"
    )


def test_permission_action_user_and_new_changed_set_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(omdlib.main, "user_confirms", lambda *a: False)  # noqa: ARG005
    assert (
        omdlib.main.permission_action(
            site_home="/tmp",
            conflict_mode=Skeleton.ASK,
            relpath="my/file",
            old_type="file",
            new_type="file",
            user_type="file",
            old_perm=123,
            new_perm=124,
            user_perm=125,
        )
        == "default"
    )


def test_permission_action_new_changed_set_default() -> None:
    assert (
        omdlib.main.permission_action(
            site_home="/tmp",
            conflict_mode=Skeleton.ASK,
            relpath="my/file",
            old_type="file",
            new_type="file",
            user_type="file",
            old_perm=123,
            new_perm=124,
            user_perm=123,
        )
        == "default"
    )


def test_permission_action_user_changed_no_action() -> None:
    assert (
        omdlib.main.permission_action(
            site_home="/tmp",
            conflict_mode=Skeleton.ASK,
            relpath="my/file",
            old_type="file",
            new_type="file",
            user_type="file",
            old_perm=123,
            new_perm=123,
            user_perm=124,
        )
        is None
    )


def test_permission_action_old_and_new_changed_set_to_new() -> None:
    assert (
        omdlib.main.permission_action(
            site_home="/tmp",
            conflict_mode=Skeleton.ASK,
            relpath="my/file",
            old_type="file",
            new_type="file",
            user_type="file",
            old_perm=123,
            new_perm=124,
            user_perm=123,
        )
        == "default"
    )


def test_permission_action_all_changed_incl_type_ask(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(omdlib.main, "user_confirms", lambda *a: True)  # noqa: ARG005
    assert (
        omdlib.main.permission_action(
            site_home="/tmp",
            conflict_mode=Skeleton.ASK,
            relpath="my/file",
            old_type="file",
            new_type="dir",
            user_type="dir",
            old_perm=123,
            new_perm=124,
            user_perm=125,
        )
        == "keep"
    )


def test_permission_action_all_changed_incl_type_ask_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(omdlib.main, "user_confirms", lambda *a: False)  # noqa: ARG005
    assert (
        omdlib.main.permission_action(
            site_home="/tmp",
            conflict_mode=Skeleton.ASK,
            relpath="my/file",
            old_type="file",
            new_type="dir",
            user_type="dir",
            old_perm=123,
            new_perm=124,
            user_perm=125,
        )
        == "default"
    )


def test_permission_action_directory_was_removed_in_target() -> None:
    assert (
        omdlib.main.permission_action(
            site_home="/tmp",
            conflict_mode=Skeleton.ASK,
            relpath="etc/ssl/private",
            old_type="dir",
            new_type=None,
            user_type="dir",
            old_perm=123,
            new_perm=0,
            user_perm=123,
        )
        is None
    )


def test_permission_action_directory_was_removed_in_both() -> None:
    assert (
        omdlib.main.permission_action(
            site_home="/tmp",
            conflict_mode=Skeleton.ASK,
            relpath="etc/ssl/private",
            old_type="dir",
            new_type=None,
            user_type=None,
            old_perm=123,
            new_perm=0,
            user_perm=123,
        )
        is None
    )


# In 2.2 we removed world permissions from all the skel files. Some sites
# had permissions that were different from previous defaults, resulting in
# repeated questions to users which they should not be asked. See CMK-12090.
@pytest.mark.parametrize(
    "relpath",
    [
        "local/share/nagvis/htdocs/userfiles/images/maps",
        "local/share/nagvis/htdocs/userfiles/images/shapes",
        "etc/check_mk/multisite.d",
        "etc/check_mk/conf.d",
        "etc/check_mk/conf.d/wato",
        "etc/ssl/private",
        "etc/ssl/certs",
    ],
)
def test_permission_action_all_changed_streamline_standard_directories(relpath: str) -> None:
    assert (
        omdlib.main.permission_action(
            site_home="/tmp",
            conflict_mode=Skeleton.ASK,
            relpath=relpath,
            old_type="dir",
            new_type="dir",
            user_type="dir",
            old_perm=0o775,
            new_perm=0o770,
            user_perm=0o750,
        )
        == "default"
    )
