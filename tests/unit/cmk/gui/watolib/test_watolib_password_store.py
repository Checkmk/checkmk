#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.password_store import Password

from cmk.gui import userdb
from cmk.gui.watolib.password_store import join_password_specs, PasswordStore, split_password_specs


def test_join_password_specs() -> None:
    meta_data: dict[str, Password] = {
        "asd": {
            "title": "Title",
            "comment": "Comment",
            "docu_url": "http://no/url",
            "password": "",
            "owned_by": None,
            "shared_with": [],
        }
    }
    passwords = {"asd": "$ecret"}
    joined = join_password_specs(meta_data, passwords)
    assert joined == {
        "asd": {
            "title": "Title",
            "comment": "Comment",
            "docu_url": "http://no/url",
            "password": "$ecret",
            "owned_by": None,
            "shared_with": [],
        }
    }


def test_join_password_missing_password() -> None:
    meta_data: dict[str, Password] = {
        "asd": {
            "title": "Title",
            "comment": "Comment",
            "docu_url": "http://no/url",
            "password": "",
            "owned_by": None,
            "shared_with": [],
        }
    }
    assert join_password_specs(meta_data, {}) == meta_data


def test_join_password_specs_missing_meta_data() -> None:
    meta_data: dict[str, Password] = {}
    passwords = {"asd": "$ecret"}
    assert join_password_specs(meta_data, passwords) == {}


def test_split_password_specs() -> None:
    meta_data, passwords = split_password_specs(
        {
            "asd": {
                "title": "Title",
                "comment": "Comment",
                "docu_url": "http://no/url",
                "password": "$ecret",
                "owned_by": None,
                "shared_with": [],
            }
        }
    )

    assert meta_data == {
        "asd": {
            "title": "Title",
            "comment": "Comment",
            "docu_url": "http://no/url",
            "password": "",
            "owned_by": None,
            "shared_with": [],
        }
    }
    assert passwords == {"asd": "$ecret"}


@pytest.fixture(name="store")
def fixture_store() -> PasswordStore:
    return PasswordStore()


def test_password_store_save(store: PasswordStore) -> None:
    entries = {
        "ding": Password(
            {
                "title": "Title",
                "comment": "Comment",
                "docu_url": "http://no/url",
                "password": "$ecret",
                "owned_by": None,
                "shared_with": [],
            }
        )
    }
    store.save(entries)

    assert store.load_for_reading() == entries


@pytest.fixture(name="test_store")
def fixture_test_store(store) -> PasswordStore:
    entries = {
        "ding": Password(
            {
                "title": "Title",
                "comment": "Comment",
                "docu_url": "http://no/url",
                "password": "$ecret",
                "owned_by": "group1",
                "shared_with": ["group2"],
            }
        )
    }
    store.save(entries)
    return store


@pytest.mark.usefixtures("with_admin_login")
def test_password_store_filter_usable_entries_by_permission(
    test_store: PasswordStore,
):
    assert test_store.filter_usable_entries(test_store.load_for_reading()) != {}


@pytest.mark.usefixtures("with_user_login")
def test_password_store_filter_usable_entries_not_permitted(
    test_store: PasswordStore,
):
    assert test_store.filter_usable_entries(test_store.load_for_reading()) == {}


@pytest.mark.usefixtures("with_user_login")
def test_password_store_filter_usable_entries_shared_with_user_group(
    test_store: PasswordStore, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(userdb, "contactgroups_of_user", lambda u: ["group2"])
    assert test_store.filter_usable_entries(test_store.load_for_reading()) != {}


@pytest.mark.usefixtures("with_user_login")
def test_password_store_filter_usable_entries_owned_by_user_group(
    test_store: PasswordStore, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(userdb, "contactgroups_of_user", lambda u: ["group1"])
    assert test_store.filter_usable_entries(test_store.load_for_reading()) != {}


@pytest.mark.usefixtures("with_admin_login")
def test_password_store_filter_editable_entries_by_permission(
    test_store: PasswordStore,
):
    assert test_store.filter_editable_entries(test_store.load_for_reading()) != {}


@pytest.mark.usefixtures("with_user_login")
def test_password_store_filter_editable_entries_not_permitted(
    test_store: PasswordStore,
):
    assert test_store.filter_editable_entries(test_store.load_for_reading()) == {}


@pytest.mark.usefixtures("with_user_login")
def test_password_store_filter_editable_entries_shared_with_user_group(
    test_store: PasswordStore, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(userdb, "contactgroups_of_user", lambda u: ["group2"])
    assert test_store.filter_editable_entries(test_store.load_for_reading()) == {}


@pytest.mark.usefixtures("with_user_login")
def test_password_store_filter_editable_entries_owned_by_user_group(
    test_store: PasswordStore, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(userdb, "contactgroups_of_user", lambda u: ["group1"])
    assert test_store.filter_editable_entries(test_store.load_for_reading()) != {}
