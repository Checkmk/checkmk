#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from collections.abc import Iterable
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from cmk.ccc.user import UserId

import cmk.utils.paths

from cmk.gui.userdb._user_profile_cleanup import cleanup_abandoned_profiles


@pytest.fixture(name="user_id")
def fixture_user_id(with_user: tuple[UserId, str]) -> UserId:
    return with_user[0]


def create_new_profile_dir(paths: Iterable[Path]) -> Path:
    profile_dir = cmk.utils.paths.profile_dir / "profile"
    assert not profile_dir.exists()
    profile_dir.mkdir()
    for path in paths:
        (profile_dir / path.with_suffix(".mk")).touch()
    return profile_dir


def touch_profile_files(profile_dir: Path, file_times: datetime) -> None:
    assert profile_dir.exists()
    timestamp = file_times.timestamp()
    for path in profile_dir.glob("*.mk"):
        os.utime(path, (timestamp, timestamp))


def test_cleanup_user_profiles_keep_recently_updated(user_id: UserId) -> None:
    now = datetime.now()
    profile_dir = create_new_profile_dir([Path("bla")])
    touch_profile_files(profile_dir, now - timedelta(days=10))
    cleanup_abandoned_profiles(now, timedelta(days=30))
    assert profile_dir.exists()


def test_cleanup_user_profiles_remove_empty(user_id: UserId) -> None:
    now = datetime.now()
    profile_dir = create_new_profile_dir([])
    touch_profile_files(profile_dir, now - timedelta(days=10))
    cleanup_abandoned_profiles(now, timedelta(days=30))
    assert not profile_dir.exists()


def test_cleanup_user_profiles_remove_abandoned(user_id: UserId) -> None:
    now = datetime.now()
    profile_dir = create_new_profile_dir([Path("bla")])
    touch_profile_files(profile_dir, now - timedelta(days=50))
    cleanup_abandoned_profiles(now, timedelta(days=30))
    assert not profile_dir.exists()


def test_cleanup_user_profiles_keep_active_profile(user_id: UserId) -> None:
    now = datetime.now()
    profile_dir = cmk.utils.paths.profile_dir / user_id
    touch_profile_files(profile_dir, now - timedelta(days=10))
    cleanup_abandoned_profiles(now, timedelta(days=30))
    assert profile_dir.exists()


def test_cleanup_user_profiles_keep_active_profile_old(user_id: UserId) -> None:
    now = datetime.now()
    profile_dir = cmk.utils.paths.profile_dir / user_id
    touch_profile_files(profile_dir, now - timedelta(days=50))
    cleanup_abandoned_profiles(now, timedelta(days=30))
    assert profile_dir.exists()
