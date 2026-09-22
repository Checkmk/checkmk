#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Tests for the Maps FormSpec building and value translation."""

import pytest

from cmk.ccc.user import UserId
from cmk.maps.gui import _settings
from cmk.maps.gui._form_schemas import (
    _build_spec,
    FormSchemaName,
    parse_form_values,
    render_form_schema,
)
from cmk.rulesets.v1.form_specs import Dictionary

# Every required element of the metadata form, in the shape the map is stored
# in. A partial bag would be refused for the missing fields, which would hide
# what these tests are about.
_STORED_METADATA = {
    "alias": "Datacenter Munich",
    "connection_id": "live_1",
    "default_z": 1,
    "render_mode": "nagvis_classic",
    "rotation_interval": ("off", None),
    "click_action": True,
    "show_in_lists": True,
}


@pytest.fixture(name="no_connections")
def _no_connections(monkeypatch: pytest.MonkeyPatch) -> None:
    # No connections configured: the effective settings still carry every Maps
    # global (default_globals), so the accessor never has to defend against a
    # missing key.
    monkeypatch.setattr(_settings, "effective_settings", lambda: {"maps_connections": []})


@pytest.mark.parametrize("spec_name", ["map_metadata", "map_bulk_metadata", "flow_view"])
@pytest.mark.usefixtures("no_connections")
def test_build_spec_returns_dictionary_for_known_names(spec_name: FormSchemaName) -> None:
    assert isinstance(_build_spec(spec_name), Dictionary)


@pytest.mark.usefixtures("request_context", "no_connections")
def test_a_stored_value_comes_back_unchanged_from_the_form_and_back(
    with_admin_login: UserId,  # noqa: ARG001
) -> None:
    _schema, for_form = render_form_schema("map_metadata", _STORED_METADATA)

    stored_again, messages = parse_form_values("map_metadata", for_form)

    assert messages == []
    assert stored_again is not None
    assert stored_again["render_mode"] == "nagvis_classic"


@pytest.mark.usefixtures("request_context", "no_connections")
def test_a_choice_the_form_does_not_offer_is_reported_as_a_validation_message(
    with_admin_login: UserId,  # noqa: ARG001
) -> None:
    refused: dict[str, object] = {**_STORED_METADATA, "render_mode": "no-such-mode"}

    parsed, messages = parse_form_values("map_metadata", refused)

    assert parsed is None
    assert [list(message.location) for message in messages] == [["render_mode"]]
