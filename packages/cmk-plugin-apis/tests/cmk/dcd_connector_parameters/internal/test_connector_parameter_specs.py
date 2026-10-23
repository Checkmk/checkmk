#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.dcd_connector_parameters.internal import connector_parameter_specs, entry_point_prefixes
from cmk.dcd_connector_parameters.internal.connector_parameter_specs import FolderChoices
from cmk.rulesets.v1 import form_specs


def _make_form_spec(_folder_choices: FolderChoices) -> form_specs.Dictionary:
    return form_specs.Dictionary(elements={})


def test_connector_parameters_spec_stores_all_fields() -> None:
    spec = connector_parameter_specs.ConnectorParametersSpec(
        name="test",
        title="Test Connector",
        description="A test connector",
        form_spec=_make_form_spec,
    )
    assert spec.name == "test"
    assert spec.title == "Test Connector"
    assert spec.description == "A test connector"


def test_connector_parameters_spec_form_spec_is_callable() -> None:
    spec = connector_parameter_specs.ConnectorParametersSpec(
        name="test",
        title="Test",
        description="Test",
        form_spec=_make_form_spec,
    )
    result = spec.form_spec(list)
    assert isinstance(result, form_specs.Dictionary)


def test_connector_parameters_spec_name_used_by_discovery() -> None:
    spec = connector_parameter_specs.ConnectorParametersSpec(
        name="my_connector",
        title="My Connector",
        description="desc",
        form_spec=_make_form_spec,
    )
    assert spec.name == "my_connector"


def test_entry_point_prefixes_contains_connector_parameters_spec() -> None:
    prefixes = entry_point_prefixes()
    assert connector_parameter_specs.ConnectorParametersSpec in prefixes


def test_entry_point_prefix_for_connector_parameters_spec() -> None:
    prefixes = entry_point_prefixes()
    assert prefixes[connector_parameter_specs.ConnectorParametersSpec] == "connector_params_"
