#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import typing

import pytest

from cmk.gui.exceptions import MKUserError
from cmk.gui.utils.rule_specs.legacy_converter import _convert_to_legacy_valuespec
from cmk.gui.valuespec import definitions
from cmk.gui.valuespec.to_formspec import valuespec_to_formspec

from cmk.rulesets.v1.form_specs.validators import ValidationError


@pytest.mark.parametrize(
    ["vs_instance", "input_value", "raises_exception"],
    [
        (definitions.Integer(), 15, False),
        (definitions.Integer(), "foo", True),
        (definitions.ListOf(definitions.Integer()), [1], False),
        (definitions.ListOf(definitions.Integer()), ["1"], True),
    ],
)
def test_convert_integer(
    vs_instance: definitions.ValueSpec,
    input_value: typing.Any,
    raises_exception: bool,
) -> None:
    fs_inst = valuespec_to_formspec(vs_instance)

    if fs_inst.custom_validate is None:
        raise RuntimeError(f"No validator on FormSpec {fs_inst}")

    if raises_exception:
        # We make sure that both validators fail if they should.
        with pytest.raises(MKUserError):
            vs_instance.validate_datatype(input_value, "")

        with pytest.raises(ValidationError):
            _ = [val(input_value) for val in fs_inst.custom_validate]
    else:
        # and both pass if they should.
        vs_instance.validate_datatype(input_value, "")
        _ = [val(input_value) for val in fs_inst.custom_validate]


@pytest.mark.parametrize(
    ["vs_instance", "expected_vs_instance"],
    [
        pytest.param(definitions.TextInput(default_value="17", size=35), None),
        pytest.param(definitions.Checkbox(default_value=False), None),
        pytest.param(definitions.Float(default_value=17.17), None),
        pytest.param(definitions.Integer(default_value=17), None),
        pytest.param(definitions.ListOf(definitions.Integer()), None),
        pytest.param(definitions.HostState(), None),
        pytest.param(
            definitions.Dictionary(elements=[("int", definitions.Integer())]),
            None,
            marks=pytest.mark.skip(
                "FIXME: FormSpec Dictionaries are wrapped in a Transform during conversion to "
                "render DictGroups as additional Dictionaries without changing the data model."
            ),
        ),
        pytest.param(
            definitions.ListChoice([("foo", "Show foo"), ("bar", "Show bar")]),
            None,
            marks=pytest.mark.skip(
                "FIXME: FormSpec ListChoice are wrapped in a Transform during conversion to "
                "correctly handle Sequence[str] values converting them to lists."
            ),
        ),
        pytest.param(
            definitions.CascadingDropdown(
                # NOTE
                # The case of no_preselect_title = None is not supported!
                # The setting of no_elements_text is not supported!
                no_preselect_title="Bitte auswählen.",  # necessary
                choices=[
                    ("first", "The first choice.", definitions.TextInput(size=35)),
                    ("second", "The second choice.", definitions.Integer()),
                    ("third", "The third choice.", definitions.Float()),
                ],
            ),
            None,
        ),
        pytest.param(
            definitions.CascadingDropdown(
                # NOTE
                # The case of no_preselect_title = None is not supported!
                # The setting of no_elements_text is not supported!
                # no_preselect_title="Bitte auswählen.",  # necessary
                default_value="first",
                choices=[
                    ("first", "The first choice.", definitions.TextInput()),
                    ("second", "The second choice.", definitions.Integer()),
                    ("third", "The third choice.", definitions.Float()),
                ],
            ),
            None,
            marks=pytest.mark.skip(
                "FIXME: The structure of default_value is different after converting back from "
                "FormSpec to ValueSpec."
            ),
        ),
        pytest.param(
            definitions.DatePicker(),
            None,
            marks=pytest.mark.skip("Not implemented in legacy_converter.py"),
        ),
        pytest.param(
            definitions.Url(default_scheme="https", allowed_schemes=["https", "http"]),
            None,
            marks=pytest.mark.skip(
                "Conversion back results in a TextInput because FormSpec doens't have a native Url type."
            ),
        ),
        pytest.param(
            definitions.Age(),
            definitions.TimeSpan(),
        ),
        pytest.param(
            definitions.Filesize(),
            definitions.LegacyDataSize(
                units=[
                    definitions.LegacyBinaryUnit.Byte,
                    definitions.LegacyBinaryUnit.KiB,
                    definitions.LegacyBinaryUnit.MiB,
                    definitions.LegacyBinaryUnit.GiB,
                    definitions.LegacyBinaryUnit.TiB,
                ]
            ),
        ),
    ],
)
def test_convert_round_trip(
    vs_instance: definitions.ValueSpec,
    expected_vs_instance: definitions.ValueSpec | None,
) -> None:
    def localizer(s: str) -> str:
        return s

    if expected_vs_instance is None:
        expected_vs_instance = vs_instance

    vs_instance2 = _convert_to_legacy_valuespec(
        valuespec_to_formspec(vs_instance),
        localizer=localizer,
    )
    try:
        _compare_value(expected_vs_instance, vs_instance2)
    except ValueError as exc:
        raise ValueError(f"Instance {vs_instance}: {exc}") from exc


def _compare_value(expected_value: object, value: object) -> None:
    blacklist = ("_validate", "_bounds", "_renderer", "_render_function")
    if callable(value):
        value = value()

    if callable(expected_value):
        expected_value = expected_value()

    if isinstance(value, (list, tuple)) and isinstance(expected_value, (list, tuple)):
        for entry1, entry2 in zip(value, expected_value):
            try:
                _compare_value(entry2, entry1)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Instance: {value} Entry: {value}: {exc}") from exc
        return

    if isinstance(value, definitions.ValueSpec) and isinstance(
        expected_value, definitions.ValueSpec
    ):
        assert isinstance(value, definitions.ValueSpec)
        assert isinstance(expected_value, definitions.ValueSpec)
        assert expected_value.__class__ == value.__class__
        for key, value1_attr in value.__dict__.items():
            if key.startswith("__"):
                continue
            if key in blacklist:
                continue
            value2_attr = getattr(expected_value, key)
            try:
                _compare_value(value2_attr, value1_attr)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Instance: {value} Key {key}: {exc}") from exc
        return

    if (value or expected_value) and value != expected_value:
        if isinstance(expected_value, definitions.Sentinel) and not value:
            # NOTE: legacy_converter can't distinguish between "no default" and "empty default" on
            # some classes.
            return
        raise ValueError(f"Values are different: {expected_value} != {value}")
