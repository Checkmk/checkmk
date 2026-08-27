#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging

import pytest

from cmk.ccc.user import UserId
from cmk.gui.exceptions import MKUserError
from cmk.gui.utils.roles import UserPermissions
from cmk.update_config.plugins.lib import pagetypes as pagetypes_update
from cmk.update_config.plugins.lib.pagetypes import (
    PreUpdatePagetypes,
    unconverted_file_name,
    UpdatePagetypes,
)
from cmk.update_config.plugins.pre_actions.utils import ConflictMode
from cmk.update_config.registry import PreUpdateAction, UpdateAction

_OWNER = UserId("harri")


class _FakePage:
    def __init__(self, name: str) -> None:
        self.name_ = name

    def name(self) -> str:
        return self.name_

    def owner(self) -> UserId:
        return _OWNER


class _FakePageType:
    raw_pages: dict[tuple[UserId, str], dict[str, object]] = {}
    saved_owners: list[UserId] = []

    @classmethod
    def type_name(cls) -> str:
        return "fake_page"

    @classmethod
    def load_raw(cls) -> dict[tuple[UserId, str], dict[str, object]]:
        return dict(cls.raw_pages)

    @classmethod
    def deserialize(cls, page_dict: dict[str, object]) -> _FakePage:
        if page_dict.get("broken"):
            raise ValueError("cannot read this page")
        return _FakePage(str(page_dict["name"]))

    @classmethod
    def save_user_instances(cls, instances: object, permissions: object, owner: UserId) -> None:
        cls.saved_owners.append(owner)


class _FakeUpdater:
    def __init__(self) -> None:
        self.target_type = _FakePageType

    def update_raw_page_dict(self, page_dict: dict[str, object]) -> dict[str, object]:
        if page_dict.get("unconvertible"):
            raise ValueError("no counterpart in the new format")
        return {**page_dict, "converted": True}


@pytest.fixture(name="fake_pages")
def fixture_fake_pages(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, dict[str, object]]]:
    parked: list[tuple[str, dict[str, object]]] = []
    monkeypatch.setattr(
        pagetypes_update,
        "save_user_file",
        lambda name, data, user_id: parked.append((name, dict(data))),
    )
    monkeypatch.setattr(
        UserPermissions,
        "from_config",
        classmethod(lambda cls, *_args: UserPermissions({}, {}, {}, [])),
    )
    _FakePageType.saved_owners = []
    return parked


def _action() -> UpdateAction:
    return UpdatePagetypes(  # type: ignore[type-var]
        name="fake", title="Fake", sort_index=1, updater=_FakeUpdater()
    )


def test_a_graph_that_cannot_be_converted_does_not_stop_the_others(
    fake_pages: list[tuple[str, dict[str, object]]],
) -> None:
    _FakePageType.raw_pages = {
        (_OWNER, "good"): {"name": "good"},
        (_OWNER, "bad"): {"name": "bad", "unconvertible": True},
    }

    _action()(logging.getLogger(__name__))

    assert _FakePageType.saved_owners == [_OWNER]
    assert fake_pages == [
        (unconverted_file_name("fake_page"), {"bad": {"name": "bad", "unconvertible": True}})
    ]


def test_a_page_that_cannot_be_read_after_conversion_is_parked_in_its_old_format(
    fake_pages: list[tuple[str, dict[str, object]]],
) -> None:
    _FakePageType.raw_pages = {(_OWNER, "bad"): {"name": "bad", "broken": True}}

    _action()(logging.getLogger(__name__))

    # The original dict is parked, not the half-converted one.
    assert fake_pages == [
        (unconverted_file_name("fake_page"), {"bad": {"name": "bad", "broken": True}})
    ]


def test_nothing_is_parked_when_every_page_converts(
    fake_pages: list[tuple[str, dict[str, object]]],
) -> None:
    _FakePageType.raw_pages = {(_OWNER, "good"): {"name": "good"}}

    _action()(logging.getLogger(__name__))

    assert fake_pages == []


def _pre_action() -> PreUpdateAction:
    return PreUpdatePagetypes(  # type: ignore[type-var]
        name="fake",
        title="Fake",
        sort_index=1,
        updater=_FakeUpdater(),
        element_name="fake page",
    )


def test_the_pre_update_check_aborts_on_a_page_it_cannot_convert() -> None:
    _FakePageType.raw_pages = {(_OWNER, "bad"): {"name": "bad", "unconvertible": True}}

    with pytest.raises(MKUserError):
        _pre_action()(logging.getLogger(__name__), ConflictMode.ABORT)


def test_the_pre_update_check_lets_a_forced_update_through() -> None:
    _FakePageType.raw_pages = {(_OWNER, "bad"): {"name": "bad", "unconvertible": True}}

    _pre_action()(logging.getLogger(__name__), ConflictMode.FORCE)


def test_the_pre_update_check_passes_when_every_page_converts() -> None:
    _FakePageType.raw_pages = {(_OWNER, "good"): {"name": "good"}}

    _pre_action()(logging.getLogger(__name__), ConflictMode.ABORT)
