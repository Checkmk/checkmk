#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

import cmk.utils.paths
from cmk.ccc.user import UserId
from cmk.gui import userdb
from cmk.gui.logged_in import LoggedInUser, UserDefaultConfig
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.watolib.predefined_conditions import (
    PredefinedConditionSpec,
    PredefinedConditionStore,
)


@pytest.fixture(autouse=True)
def profile_dir() -> None:
    cmk.utils.paths.profile_dir.mkdir(parents=True, exist_ok=True)


def _user(explicitly_given_permissions: frozenset[str] = frozenset()) -> LoggedInUser:
    return LoggedInUser(
        UserId("some_user"),
        UserPermissions({}, {}, {}, []),
        defaults=UserDefaultConfig(
            users={}, default_language="en", default_show_mode="default_show_less"
        ),
        explicitly_given_permissions=explicitly_given_permissions,
    )


def _admin() -> LoggedInUser:
    return _user(frozenset({"wato.edit_all_predefined_conditions"}))


def _condition(owned_by: str | None, shared_with: Sequence[str]) -> PredefinedConditionSpec:
    return PredefinedConditionSpec(
        title="Title",
        comment="Comment",
        docu_url="http://no/url",
        conditions={"host_folder": ""},
        owned_by=owned_by,
        shared_with=shared_with,
    )


@pytest.fixture(name="test_store")
def fixture_test_store() -> PredefinedConditionStore:
    store = PredefinedConditionStore()
    store.save(
        {
            "owned": _condition(owned_by="group1", shared_with=[]),
            "shared": _condition(owned_by="other_group", shared_with=["group2", "group3"]),
            "unrelated": _condition(owned_by="other_group", shared_with=["other_group2"]),
        },
        pprint_value=False,
    )
    return store


def test_filter_usable_entries_with_permission(test_store: PredefinedConditionStore) -> None:
    assert set(test_store.filter_usable_entries(test_store.load_for_reading(), _admin())) == {
        "owned",
        "shared",
        "unrelated",
    }


def test_filter_usable_entries_owned_and_shared(
    test_store: PredefinedConditionStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(userdb, "contactgroups_of_user", lambda u: ["group1", "group2"])
    assert set(test_store.filter_usable_entries(test_store.load_for_reading(), _user())) == {
        "owned",
        "shared",
    }


def test_filter_usable_entries_shared_but_not_owned(
    test_store: PredefinedConditionStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(userdb, "contactgroups_of_user", lambda u: ["group2"])
    assert set(test_store.filter_usable_entries(test_store.load_for_reading(), _user())) == {
        "shared"
    }


def test_filter_usable_entries_no_matching_group(
    test_store: PredefinedConditionStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(userdb, "contactgroups_of_user", lambda u: ["group42"])
    assert test_store.filter_usable_entries(test_store.load_for_reading(), _user()) == {}


def test_filter_editable_entries_with_permission(test_store: PredefinedConditionStore) -> None:
    assert set(test_store.filter_editable_entries(test_store.load_for_reading(), _admin())) == {
        "owned",
        "shared",
        "unrelated",
    }


def test_filter_editable_entries_owned_by_user_group(
    test_store: PredefinedConditionStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(userdb, "contactgroups_of_user", lambda u: ["group1"])
    assert set(test_store.filter_editable_entries(test_store.load_for_reading(), _user())) == {
        "owned"
    }


def test_filter_editable_entries_excludes_shared_only(
    test_store: PredefinedConditionStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(userdb, "contactgroups_of_user", lambda u: ["group2"])
    assert test_store.filter_editable_entries(test_store.load_for_reading(), _user()) == {}
