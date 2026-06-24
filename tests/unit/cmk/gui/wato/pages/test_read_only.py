#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.user import UserId
from cmk.gui.type_defs import ReadOnlySpec
from cmk.gui.wato.pages.read_only import _ReadOnlyFormSpecAdapter

ADAPTER = _ReadOnlyFormSpecAdapter()


@pytest.mark.parametrize(
    "model",
    [
        ReadOnlySpec(enabled=False, message="", rw_users=[]),
        ReadOnlySpec(enabled=True, message="gone fishing", rw_users=[UserId("cmkadmin")]),
        ReadOnlySpec(
            enabled=(1782326418.0, 1782330018.0),
            message="maintenance",
            rw_users=[UserId("cmkadmin"), UserId("automation")],
        ),
    ],
)
def test_read_only_round_trip(model: ReadOnlySpec) -> None:
    assert ADAPTER.from_form_spec(ADAPTER.to_form_spec(model).value) == model


def test_to_form_spec_uses_plain_strings_for_users() -> None:
    form_data = ADAPTER.to_form_spec(
        ReadOnlySpec(enabled=False, message="", rw_users=[UserId("cmkadmin")])
    ).value
    assert isinstance(form_data, dict)
    assert form_data["rw_users"] == ["cmkadmin"]
    assert all(type(name) is str for name in form_data["rw_users"])


def test_from_form_spec_wraps_users_into_user_id() -> None:
    # Regression for crash SUP-29570: a plain user name string from the form
    # must be turned back into a UserId for the on-disk model.
    settings = ADAPTER.from_form_spec(
        {"enabled": ("disabled", None), "rw_users": ["cmkadmin"], "message": ""}
    )
    assert settings["rw_users"] == [UserId("cmkadmin")]
    assert all(isinstance(name, UserId) for name in settings["rw_users"])


def test_to_form_spec_maps_enabled_states() -> None:
    def _enabled(model: ReadOnlySpec) -> object:
        value = ADAPTER.to_form_spec(model).value
        assert isinstance(value, dict)
        return value["enabled"]

    assert _enabled(ReadOnlySpec(enabled=False, message="", rw_users=[])) == ("disabled", None)
    assert _enabled(ReadOnlySpec(enabled=True, message="", rw_users=[])) == ("permanent", None)
    assert _enabled(ReadOnlySpec(enabled=(1.0, 2.0), message="", rw_users=[])) == (
        "timerange",
        (1.0, 2.0),
    )


def test_from_form_spec_accepts_list_timerange_payload() -> None:
    settings = ADAPTER.from_form_spec(
        {"enabled": ("timerange", [1.0, 2.0]), "rw_users": [], "message": ""}
    )
    assert settings["enabled"] == (1.0, 2.0)


def test_from_form_spec_rejects_unknown_enabled_shape() -> None:
    with pytest.raises(ValueError):
        ADAPTER.from_form_spec({"enabled": ("bogus", None), "rw_users": [], "message": ""})
