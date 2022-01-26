#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui import userdb
from cmk.gui.watolib.password_store import Password, PasswordStore


@pytest.fixture(name="store")
def fixture_store() -> PasswordStore:
    return PasswordStore()


def test_password_store_save(store: PasswordStore):
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
