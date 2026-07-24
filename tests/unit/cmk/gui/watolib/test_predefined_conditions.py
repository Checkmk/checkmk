#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.gui import userdb
from cmk.gui.watolib.predefined_conditions import (
    PredefinedConditionSpec,
    PredefinedConditionStore,
)


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


@pytest.mark.usefixtures("with_admin_login")
def test_filter_usable_entries_with_permission(test_store: PredefinedConditionStore) -> None:
    assert set(test_store.filter_usable_entries(test_store.load_for_reading())) == {
        "owned",
        "shared",
        "unrelated",
    }


@pytest.mark.usefixtures("with_user_login")
def test_filter_usable_entries_owned_and_shared(
    test_store: PredefinedConditionStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(userdb, "contactgroups_of_user", lambda u: ["group1", "group2"])
    assert set(test_store.filter_usable_entries(test_store.load_for_reading())) == {
        "owned",
        "shared",
    }


@pytest.mark.usefixtures("with_user_login")
def test_filter_usable_entries_shared_but_not_owned(
    test_store: PredefinedConditionStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(userdb, "contactgroups_of_user", lambda u: ["group2"])
    assert set(test_store.filter_usable_entries(test_store.load_for_reading())) == {"shared"}


@pytest.mark.usefixtures("with_user_login")
def test_filter_usable_entries_no_matching_group(
    test_store: PredefinedConditionStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(userdb, "contactgroups_of_user", lambda u: ["group42"])
    assert test_store.filter_usable_entries(test_store.load_for_reading()) == {}


@pytest.mark.usefixtures("with_admin_login")
def test_filter_editable_entries_with_permission(test_store: PredefinedConditionStore) -> None:
    assert set(test_store.filter_editable_entries(test_store.load_for_reading())) == {
        "owned",
        "shared",
        "unrelated",
    }


@pytest.mark.usefixtures("with_user_login")
def test_filter_editable_entries_owned_by_user_group(
    test_store: PredefinedConditionStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(userdb, "contactgroups_of_user", lambda u: ["group1"])
    assert set(test_store.filter_editable_entries(test_store.load_for_reading())) == {"owned"}


@pytest.mark.usefixtures("with_user_login")
def test_filter_editable_entries_excludes_shared_only(
    test_store: PredefinedConditionStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(userdb, "contactgroups_of_user", lambda u: ["group2"])
    assert test_store.filter_editable_entries(test_store.load_for_reading()) == {}
