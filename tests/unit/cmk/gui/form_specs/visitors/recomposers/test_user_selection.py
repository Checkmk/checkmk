#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.user import UserId
from cmk.gui.form_specs import get_visitor, RawDiskData, RawFrontendData, VisitorOptions
from cmk.gui.form_specs.visitors.recomposers import user_selection
from cmk.gui.form_specs.visitors.single_choice import SingleChoiceVisitor
from cmk.rulesets.internal.form_specs import UserSelection


@pytest.fixture(name="known_user")
def _known_user(monkeypatch: pytest.MonkeyPatch) -> UserId:
    user_id = UserId("cmkadmin")
    monkeypatch.setattr(
        user_selection,
        "generate_wato_users_elements_function",
        lambda *args, **kwargs: lambda: [(user_id, f"{user_id} - Administrator")],
    )
    return user_id


_OPTIONS = VisitorOptions(migrate_values=False, mask_values=False)


def test_user_selection_saves_selected_user_as_plain_str(
    request_context: None, known_user: UserId
) -> None:
    # Regression for crash SUP-29570: selecting a user and saving must not raise.
    visitor = get_visitor(UserSelection(), _OPTIONS)
    selected = RawFrontendData(SingleChoiceVisitor.option_id(known_user))

    assert visitor.validate(selected) == []
    assert visitor.to_disk(selected) == "cmkadmin"


def test_user_selection_renders_stored_user(request_context: None, known_user: UserId) -> None:
    # A user name stored on disk round-trips back to its frontend selection.
    visitor = get_visitor(UserSelection(), _OPTIONS)
    stored = RawDiskData("cmkadmin")

    assert visitor.validate(stored) == []
    _spec, frontend_value = visitor.to_vue(stored)
    assert frontend_value == SingleChoiceVisitor.option_id(UserId("cmkadmin"))


def test_user_selection_rejects_unknown_user(request_context: None, known_user: UserId) -> None:
    visitor = get_visitor(UserSelection(), _OPTIONS)
    unknown = RawFrontendData(SingleChoiceVisitor.option_id(UserId("ghost")))

    assert visitor.validate(unknown) != []
