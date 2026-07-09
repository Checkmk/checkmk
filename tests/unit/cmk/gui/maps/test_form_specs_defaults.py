#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Self-consistency of the Maps authoring/settings FormSpecs.

``test_form_schemas.py`` pins the ``_build_spec`` dispatch; this pins the specs
themselves. The global-settings specs ship *complete* defaults (the editor opens
pre-filled), so their default must be free of hard validation errors — a
too-short string, an out-of-range number, or a cascade default that isn't a
listed choice would render "Global settings → Maps" un-openable, which neither
the dispatch test nor the GUI↔daemon contract test would catch.

The per-map "Map settings" specs deliberately require the operator to *pick*
a connection (no auto-prefill, unlike the global map defaults), so their default
is intentionally not submittable; for those we only pin that they build.
"""

import pytest

from cmk.gui.form_specs import DEFAULT_VALUE, get_visitor, VisitorOptions
from cmk.maps.gui.form_specs.global_settings import map_defaults_spec, object_defaults_spec
from cmk.maps.gui.form_specs.map_metadata import (
    flow_view_spec,
    map_bulk_metadata_spec,
    map_metadata_spec,
)
from cmk.rulesets.v1.form_specs import Dictionary

_CHOICES = [("cmk_local", "Local site"), ("remote_dc", "Remote DC")]

# Specs whose declared default is a complete, submittable value.
_COMPLETE_DEFAULT_SPECS: dict[str, Dictionary] = {
    "map_defaults": map_defaults_spec(_CHOICES),
    "object_defaults": object_defaults_spec(),
    "flow_view": flow_view_spec(),
}


def _hard_errors(spec: Dictionary) -> list[str]:
    """Validation messages for the spec's own default, minus optional input hints."""
    visitor = get_visitor(spec, VisitorOptions(migrate_values=True, mask_values=False))
    return [
        m.message for m in visitor.validate(DEFAULT_VALUE) if "input hint" not in m.message.lower()
    ]


@pytest.mark.parametrize("name", list(_COMPLETE_DEFAULT_SPECS))
def test_complete_default_spec_has_no_hard_validation_errors(
    name: str,
    request_context: None,  # noqa: ARG001
) -> None:
    assert _hard_errors(_COMPLETE_DEFAULT_SPECS[name]) == []


def test_map_defaults_prefills_first_connection(request_context: None) -> None:  # noqa: ARG001
    # With choices supplied, the global map-defaults spec prefills a real
    # connection id (the site's first) rather than an empty/invalid one.
    visitor = get_visitor(
        map_defaults_spec(_CHOICES), VisitorOptions(migrate_values=True, mask_values=False)
    )
    disk_default = visitor.to_disk(DEFAULT_VALUE)
    assert isinstance(disk_default, dict)
    assert disk_default["default_backend_id"] == "cmk_local"


@pytest.mark.parametrize("with_choices", [True, False])
def test_map_metadata_specs_build(with_choices: bool, request_context: None) -> None:  # noqa: ARG001
    # These require the operator to pick a connection (no auto-prefill), so their
    # default is intentionally not submittable — pin only that they build cleanly
    # both on a configured site (choices) and a fresh one (none).
    choices = _CHOICES if with_choices else None
    assert isinstance(map_metadata_spec(choices), Dictionary)
    assert isinstance(map_bulk_metadata_spec(choices), Dictionary)
