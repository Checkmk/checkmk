#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Iterable
from unittest.mock import MagicMock

import pytest

from cmk.gui.userdb.store import OpenFileMode, UserId, Users, UserSpec, UserStore


class TestUserStoreLocking:
    @pytest.fixture
    def mock_acquire_lock(self, monkeypatch: pytest.MonkeyPatch) -> Iterable[MagicMock]:
        mock_acquire_lock = MagicMock()
        monkeypatch.setattr("cmk.gui.userdb.store.acquire_lock", mock_acquire_lock)
        yield mock_acquire_lock

    @pytest.fixture
    def mock_release_lock(self, monkeypatch: pytest.MonkeyPatch) -> Iterable[MagicMock]:
        mock_release_lock = MagicMock()
        monkeypatch.setattr("cmk.utils.store.release_lock", mock_release_lock)
        yield mock_release_lock

    @pytest.fixture
    def mock_load_users_failing(self, monkeypatch: pytest.MonkeyPatch) -> Iterable[MagicMock]:
        mock_load_users = MagicMock(side_effect=Exception)
        monkeypatch.setattr("cmk.gui.userdb.store.load_users", mock_load_users)
        yield mock_load_users

    @pytest.fixture
    def mock_save_users_failing(self, monkeypatch: pytest.MonkeyPatch) -> Iterable[MagicMock]:
        mock_save_users = MagicMock(side_effect=Exception)
        monkeypatch.setattr("cmk.gui.userdb.store.save_users", mock_save_users)
        yield mock_save_users

    def test_read_mode_does_not_lock(
        self,
        mock_acquire_lock: MagicMock,
    ) -> None:
        with UserStore(OpenFileMode.READ) as _:
            ...

        assert not mock_acquire_lock.called

    def test_write_mode_acquires_and_releases_lock_when_changed(
        self, mock_acquire_lock: MagicMock, mock_release_lock: MagicMock
    ) -> None:
        with UserStore(OpenFileMode.WRITE) as user_store:
            user_store[UserId("Jen")] = UserSpec({"alias": "Jen Barber", "connector": "123"})

        assert mock_acquire_lock.called
        assert mock_release_lock.called

    def test_write_mode_acquires_and_releases_lock_when_not_changed(
        self, mock_acquire_lock: MagicMock, mock_release_lock: MagicMock
    ) -> None:
        with UserStore(OpenFileMode.WRITE) as _:
            ...

        assert mock_acquire_lock.called
        assert mock_release_lock.called

    def test_failing_load_users_releases_lock(
        self,
        mock_acquire_lock: MagicMock,
        mock_release_lock: MagicMock,
        mock_load_users_failing: MagicMock,
    ) -> None:
        with pytest.raises(Exception):
            with UserStore(OpenFileMode.WRITE) as _:
                ...

        assert mock_release_lock.called

    def test_failing_save_users_releases_lock(
        self,
        mock_acquire_lock: MagicMock,
        mock_release_lock: MagicMock,
        mock_save_users_failing: MagicMock,
    ) -> None:
        with pytest.raises(Exception):
            with UserStore(OpenFileMode.WRITE) as user_store:
                user_store[UserId("Jen")] = UserSpec({"alias": "Jen Barber", "connector": "123"})

        assert mock_release_lock.called


class TestUserStore:
    @pytest.fixture
    def user_collection(self) -> Users:
        return {
            UserId("moss"): UserSpec({"alias": "Maurice Moss", "connector": "htpasswd"}),
            UserId("roy"): UserSpec({"alias": "Roy Trenneman", "connector": "123"}),
            UserId("richmond"): UserSpec({"alias": "Richmond Avenal", "connector": "456"}),
        }

    @pytest.fixture
    def mock_load_users(
        self, monkeypatch: pytest.MonkeyPatch, user_collection: Users
    ) -> Iterable[MagicMock]:
        mock_load_users = MagicMock(return_value=user_collection)
        monkeypatch.setattr("cmk.gui.userdb.store.load_users", mock_load_users)
        yield mock_load_users

    @pytest.fixture
    def mock_save_users(self, monkeypatch: pytest.MonkeyPatch) -> Iterable[MagicMock]:
        mock_save_users = MagicMock()
        monkeypatch.setattr("cmk.gui.userdb.store.save_users", mock_save_users)
        yield mock_save_users

    def test_do_not_save_changes_in_read_mode(
        self,
        mock_load_users: MagicMock,
        mock_save_users: MagicMock,
    ) -> None:
        with UserStore(OpenFileMode.READ) as user_store:
            user_store[UserId("Jen")] = UserSpec({"alias": "Jen Barber", "connector": "123"})

        assert not mock_save_users.called

    def test_save_changes(
        self,
        mock_load_users: MagicMock,
        mock_save_users: MagicMock,
    ) -> None:
        with UserStore(OpenFileMode.WRITE) as user_store:
            user_store[UserId("Jen")] = UserSpec({"alias": "Jen Barber", "connector": "123"})

        assert mock_save_users.called

    def test_do_not_save_changes_when_not_changed(
        self,
        mock_load_users: MagicMock,
        mock_save_users: MagicMock,
        user_collection: Users,
    ) -> None:
        unmodified_user_id, unmodified_user_spec = list(user_collection.items())[0]
        with UserStore(OpenFileMode.WRITE) as user_store:
            user_store[unmodified_user_id] = unmodified_user_spec

        assert not mock_save_users.called
