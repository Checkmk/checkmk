#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.gui.config import active_config
from cmk.gui.watolib.host_attributes import (
    ABCHostAttributeFormSpec,
    ABCHostAttributeValueSpec,
    all_host_attributes,
)
from tests.testlib.unit.gui.host_attributes_test_helper import (
    assert_cases_cover_form_spec_attributes,
    assert_form_spec_attribute_lifecycle,
    assert_form_spec_attribute_rejects,
    assert_form_spec_attributes_round_trip_default_value,
    assert_form_spec_value_behavior,
    assert_round_trips,
    assert_show_in_table_attributes_paint_plain_text,
    BASE_FORM_SPEC_CASES,
    Case,
    CaseFail,
    CasePass,
    form_spec_attributes,
    RoundTrip,
    validate_form_spec_default_value,
)

# The attributes a FormSpec-native migration has to cover. Editions add their own on top.
CASES: Mapping[str, list[Case]] = BASE_FORM_SPEC_CASES


def _all_value_spec_attributes() -> dict[str, ABCHostAttributeValueSpec]:
    return {
        name: attr
        for name, attr in all_host_attributes(
            active_config.wato_host_attrs,
            active_config.tags.get_tag_groups_by_topic(),
        ).items()
        if isinstance(attr, ABCHostAttributeValueSpec)
    }


_FORM_SPEC_DEFAULT_MISMATCHES = {
    "snmp_community",
    "management_snmp_community",
}


def _validate_value_spec_default_value(attr: ABCHostAttributeValueSpec) -> RoundTrip:
    value_spec = attr.valuespec()
    default = attr.default_value()
    try:
        transformed = value_spec.transform_value(default)
    except Exception as exc:
        return RoundTrip(False, f"round-trip raised: {exc!r}")
    if transformed != default:
        return RoundTrip(
            False, f"transform_value changed the value: {transformed!r} != {default!r}"
        )
    return RoundTrip(True, "")


@pytest.mark.usefixtures("load_config")
def test_host_attribute_round_trip_default_value() -> None:
    value_spec_results: dict[str, RoundTrip] = {}
    form_spec_results: dict[str, RoundTrip] = {}
    for name, attr in _all_value_spec_attributes().items():
        value_spec_results[name] = _validate_value_spec_default_value(attr)

        form_spec_results[name] = validate_form_spec_default_value(
            attr.form_spec(), attr.default_value()
        )

    assert_round_trips("ValueSpec", value_spec_results)
    assert_round_trips("FormSpec", form_spec_results, skip=_FORM_SPEC_DEFAULT_MISMATCHES)


@pytest.mark.usefixtures("load_config")
@pytest.mark.parametrize("name", sorted(_FORM_SPEC_DEFAULT_MISMATCHES))
def test_form_spec_default_value_is_unrepresentable_none(name: str) -> None:
    """These attributes default to ``None`` in the ValueSpec, but their native FormSpec has no
    representation for ``None`` yet, so serializing the default fails."""
    attr = _all_value_spec_attributes()[name]
    assert attr.default_value() is None

    result = validate_form_spec_default_value(attr.form_spec(), None)
    assert result.ok is False
    assert "Unable to serialize invalid value" in result.detail


@pytest.mark.usefixtures("load_config")
def test_form_spec_native_attribute_round_trip_default_value() -> None:
    assert_form_spec_attributes_round_trip_default_value()


@pytest.mark.usefixtures("load_config")
def test_every_form_spec_attribute_has_cases() -> None:
    """Migrating an attribute to a native FormSpec means documenting its values here."""
    assert_cases_cover_form_spec_attributes(CASES)


@pytest.mark.usefixtures("load_config")
def test_show_in_table_attributes_are_paintable_as_plain_text() -> None:
    assert_show_in_table_attributes_paint_plain_text(CASES)


@pytest.fixture(name="form_spec_attribute")
def _fixture_form_spec_attributes(load_config: object) -> dict[str, ABCHostAttributeFormSpec]:
    return form_spec_attributes()


@pytest.mark.parametrize(
    "attr_name, case",
    [
        pytest.param(name, case, id=f"{name}-{case.id}")
        for name, cases in CASES.items()
        for case in cases
    ],
)
def test_form_spec_value_behavior(
    form_spec_attribute: dict[str, ABCHostAttributeFormSpec],
    attr_name: str,
    case: Case,
) -> None:
    assert_form_spec_value_behavior(form_spec_attribute[attr_name], case)


@pytest.mark.usefixtures("request_context")
@pytest.mark.parametrize(
    "attr_name, case",
    [
        pytest.param(name, case, id=f"{name}-{case.id}")
        for name, cases in CASES.items()
        for case in cases
        if isinstance(case, CasePass)
    ],
)
def test_form_spec_accepted_value_survives_edit_page(
    form_spec_attribute: dict[str, ABCHostAttributeFormSpec],
    attr_name: str,
    case: Case,
) -> None:
    """Render -> submit -> parse: an accepted value comes back off the page unchanged."""
    assert_form_spec_attribute_lifecycle(form_spec_attribute[attr_name], case.value)


@pytest.mark.usefixtures("request_context")
@pytest.mark.parametrize(
    "attr_name, case",
    [
        pytest.param(name, case, id=f"{name}-{case.id}")
        for name, cases in CASES.items()
        for case in cases
        if isinstance(case, CaseFail)
    ],
)
def test_form_spec_rejected_value_does_not_pass_edit_page(
    form_spec_attribute: dict[str, ABCHostAttributeFormSpec],
    attr_name: str,
    case: Case,
) -> None:
    assert_form_spec_attribute_rejects(form_spec_attribute[attr_name], case.value)
