#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Tests for the Maps FormSpec building/dispatch helpers."""

import json

import pytest

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.user import UserId
from cmk.gui.config import Config
from cmk.gui.http import request
from cmk.gui.pages import PageContext
from cmk.maps.gui import _settings
from cmk.maps.gui._form_schemas import _build_spec, AjaxMapsFormParse, AjaxMapsFormSchema
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


def _page_context(spec_name: str, values: object) -> PageContext:
    request.set_var("spec", spec_name)
    request.set_var("request", json.dumps({"data": values}))
    return PageContext(config=Config(), request=request)


@pytest.fixture(name="no_connections")
def _no_connections(monkeypatch: pytest.MonkeyPatch) -> None:
    # No connections configured: the effective settings still carry every Maps
    # global (default_globals), so the accessor never has to defend against a
    # missing key.
    monkeypatch.setattr(_settings, "effective_settings", lambda: {"maps_connections": []})


@pytest.mark.parametrize("spec_name", ["map_metadata", "map_bulk_metadata", "flow_view"])
@pytest.mark.usefixtures("no_connections")
def test_build_spec_returns_dictionary_for_known_names(spec_name: str) -> None:
    assert isinstance(_build_spec(spec_name), Dictionary)


def test_build_spec_rejects_unknown_name() -> None:
    with pytest.raises(MKGeneralException, match="Unknown Maps form spec"):
        _build_spec("nope")


@pytest.mark.usefixtures("request_context", "no_connections")
def test_a_stored_value_comes_back_unchanged_from_the_form_and_back(
    with_admin_login: UserId,  # noqa: ARG001
) -> None:
    for_form = AjaxMapsFormSchema().page(_page_context("map_metadata", _STORED_METADATA))
    assert isinstance(for_form, dict)

    stored_again = AjaxMapsFormParse().page(_page_context("map_metadata", for_form["data"]))

    assert isinstance(stored_again, dict)
    assert stored_again["data"]["render_mode"] == "nagvis_classic"


@pytest.mark.usefixtures("request_context", "no_connections")
def test_a_choice_the_form_does_not_offer_is_reported_as_a_validation_message(
    with_admin_login: UserId,  # noqa: ARG001
) -> None:
    refused: dict[str, object] = {**_STORED_METADATA, "render_mode": "no-such-mode"}

    result = AjaxMapsFormParse().page(_page_context("map_metadata", refused))

    assert isinstance(result, dict)
    assert [message["location"] for message in result["validation"]] == [["render_mode"]]
