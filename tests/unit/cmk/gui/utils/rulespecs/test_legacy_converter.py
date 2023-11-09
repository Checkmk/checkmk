#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from functools import partial

import pytest

import cmk.gui.valuespec as legacy_valuespecs
import cmk.gui.watolib.rulespecs as legacy_rulespecs
from cmk.gui import wato, watolib
from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.utils.rulespecs.legacy_converter import (
    _convert_to_legacy_rulespec_group,
    _convert_to_legacy_valuespec,
    convert_to_legacy_rulespec,
)

import cmk.rulesets.v1 as api_v1


def _v1_custom_text_validate(value: str) -> None:
    api_v1.disallow_empty(error_msg=api_v1.Localizable("Fill this"))(value)
    api_v1.match_regex(regex=r"^[^.\r\n]+$", error_msg=api_v1.Localizable("No dot allowed"))(value)

    if value == "admin":
        raise api_v1.ValidationError(api_v1.Localizable("Forbidden"))


def _legacy_custom_text_validate(value: str, varprefix: str) -> None:
    if value == "admin":
        raise MKUserError(varprefix, _("Forbidden"))


@pytest.mark.parametrize(
    ["new_valuespec", "expected"],
    [
        pytest.param(
            api_v1.MonitoringState(),
            legacy_valuespecs.MonitoringState(),
            id="minimal MonitoringState",
        ),
        pytest.param(
            api_v1.MonitoringState(
                title=api_v1.Localizable("title"),
                label=api_v1.Localizable("label"),
                help_text=api_v1.Localizable("help text"),
            ),
            legacy_valuespecs.MonitoringState(
                title=_("title"),
                label=_("label"),
                help=_("help text"),
                default_value=0,
            ),
            id="MonitoringState",
        ),
        pytest.param(
            api_v1.Dictionary(elements={}),
            legacy_valuespecs.Dictionary(elements=[]),
            id="minimal Dictionary",
        ),
        pytest.param(
            api_v1.Dictionary(
                elements={
                    "key_req": api_v1.DictElement(
                        api_v1.MonitoringState(title=api_v1.Localizable("title")),
                        required=True,
                    ),
                    "key_opt": api_v1.DictElement(
                        api_v1.MonitoringState(title=api_v1.Localizable("title")),
                        show_more=True,
                    ),
                    "key_read_only": api_v1.DictElement(
                        api_v1.MonitoringState(title=api_v1.Localizable("title")),
                        read_only=True,
                    ),
                },
                title=api_v1.Localizable("Configuration title"),
                help_text=api_v1.Localizable("Helpful description"),
                deprecated_elements=["old_key", "another_old_key"],
                no_elements_text=api_v1.Localizable("No elements specified"),
            ),
            legacy_valuespecs.Dictionary(
                elements=[
                    ("key_req", legacy_valuespecs.MonitoringState(title=_("title"))),
                    ("key_opt", legacy_valuespecs.MonitoringState(title=_("title"))),
                    ("key_read_only", legacy_valuespecs.MonitoringState(title=_("title"))),
                ],
                title=_("Configuration title"),
                help=_("Helpful description"),
                empty_text=_("No elements specified"),
                required_keys=["key_req"],
                show_more_keys=["key_opt"],
                hidden_keys=["key_read_only"],
                ignored_keys=["old_key", "another_old_key"],
            ),
            id="Dictionary",
        ),
        pytest.param(
            api_v1.Integer(),
            legacy_valuespecs.Integer(),
            id="minimal Integer",
        ),
        pytest.param(
            api_v1.Integer(
                title=api_v1.Localizable("title"),
                help_text=api_v1.Localizable("help"),
                label=api_v1.Localizable("label"),
                unit=api_v1.Localizable("days"),
                default_value=-1,
                custom_validate=lambda x: None,
            ),
            legacy_valuespecs.Integer(
                title=_("title"),
                help=_("help"),
                label=_("label"),
                unit=_("days"),
                default_value=-1,
                validate=lambda x, y: None,
            ),
            id="Integer",
        ),
        pytest.param(
            api_v1.Percentage(),
            legacy_valuespecs.Percentage(),
            id="minimal Percentage",
        ),
        pytest.param(
            api_v1.Percentage(
                title=api_v1.Localizable("title"),
                help_text=api_v1.Localizable("help"),
                label=api_v1.Localizable("label"),
                display_precision=2,
                default_value=-1.0,
                custom_validate=lambda x: None,
            ),
            legacy_valuespecs.Percentage(
                title=_("title"),
                help=_("help"),
                label=_("label"),
                display_format="%.2f",
                default_value=-1.0,
                validate=lambda x, y: None,
            ),
            id="Percentage",
        ),
        pytest.param(
            api_v1.TextInput(),
            legacy_valuespecs.TextInput(),
            id="minimal TextInput",
        ),
        pytest.param(
            api_v1.TextInput(
                title=api_v1.Localizable("spec title"),
                label=api_v1.Localizable("spec label"),
                input_hint="firstname",
                help_text=api_v1.Localizable("help text"),
                default_value="myname",
                custom_validate=_v1_custom_text_validate,
            ),
            legacy_valuespecs.TextInput(
                title=_("spec title"),
                label=_("spec label"),
                placeholder="firstname",
                help=_("help text"),
                default_value="myname",
                validate=_legacy_custom_text_validate,
            ),
            id="TextInput",
        ),
        pytest.param(
            api_v1.Tuple(elements=[]),
            legacy_valuespecs.Tuple(elements=[]),
            id="minimal Tuple",
        ),
        pytest.param(
            api_v1.Tuple(
                elements=[
                    api_v1.TextInput(title=api_v1.Localizable("child title 1")),
                    api_v1.TextInput(title=api_v1.Localizable("child title 2")),
                ],
                title=api_v1.Localizable("parent title"),
                help_text=api_v1.Localizable("parent help"),
            ),
            legacy_valuespecs.Tuple(
                elements=[
                    legacy_valuespecs.TextInput(title=_("child title 1")),
                    legacy_valuespecs.TextInput(title=_("child title 2")),
                ],
                title=_("parent title"),
                help=_("parent help"),
            ),
            id="Tuple",
        ),
        pytest.param(
            api_v1.DropdownChoice(elements=[]),
            legacy_valuespecs.DropdownChoice(choices=[], invalid_choice="complain"),
            id="minimal DropdownChoice",
        ),
        pytest.param(
            api_v1.DropdownChoice(
                elements=[
                    api_v1.DropdownChoiceElement(
                        choice=True, display=api_v1.Localizable("Enabled")
                    ),
                    api_v1.DropdownChoiceElement(
                        choice=False, display=api_v1.Localizable("Disabled")
                    ),
                ],
                no_elements_text=api_v1.Localizable("No elements"),
                deprecated_elements=[],
                frozen=True,
                title=api_v1.Localizable("title"),
                label=api_v1.Localizable("label"),
                help_text=api_v1.Localizable("help text"),
                default_element=True,
                invalid_element_validation=api_v1.InvalidElementValidator(
                    mode=api_v1.InvalidElementMode.KEEP,
                    display=api_v1.Localizable("invalid choice title"),
                    error_msg=api_v1.Localizable("invalid choice msg"),
                ),
            ),
            legacy_valuespecs.DropdownChoice(
                choices=[(True, _("Enabled")), (False, _("Disabled"))],
                empty_text=_("No elements"),
                deprecated_choices=[],
                read_only=True,
                title=_("title"),
                label=_("label"),
                help=_("help text"),
                default_value=True,
                invalid_choice=None,
                invalid_choice_title=_("invalid choice title"),
                invalid_choice_error=_("invalid choice msg"),
            ),
            id="DropdownChoice",
        ),
        pytest.param(
            api_v1.CascadingDropdown(elements=[], default_element=None),
            legacy_valuespecs.CascadingDropdown(choices=[], no_preselect_title=""),
            id="minimal CascadingDropdown",
        ),
        pytest.param(
            api_v1.CascadingDropdown(
                elements=[
                    api_v1.CascadingDropdownElement(ident="first", value_spec=api_v1.TextInput())
                ],
                default_element=None,
            ),
            legacy_valuespecs.CascadingDropdown(
                choices=[("first", "first", legacy_valuespecs.TextInput())],
                no_preselect_title="",
            ),
            id="CascadingDropdown no valuespec title",
        ),
        pytest.param(
            api_v1.CascadingDropdown(
                elements=[
                    api_v1.CascadingDropdownElement(
                        ident="first",
                        value_spec=api_v1.TextInput(title=api_v1.Localizable("Spec title")),
                    )
                ],
                default_element=None,
            ),
            legacy_valuespecs.CascadingDropdown(
                choices=[
                    ("first", _("Spec title"), legacy_valuespecs.TextInput(title=_("Spec title")))
                ],
                no_preselect_title="",
            ),
            id="CascadingDropdown valuespec title",
        ),
        pytest.param(
            api_v1.CascadingDropdown(
                elements=[
                    api_v1.CascadingDropdownElement(
                        ident="first",
                        value_spec=api_v1.TextInput(),
                    )
                ],
                title=api_v1.Localizable("parent title"),
                help_text=api_v1.Localizable("parent help"),
                label=api_v1.Localizable("parent label"),
                default_element="first",
            ),
            legacy_valuespecs.CascadingDropdown(
                choices=[("first", _("first"), legacy_valuespecs.TextInput())],
                title=_("parent title"),
                help=_("parent help"),
                label=_("parent label"),
                default_value="first",
            ),
            id="CascadingDropdown",
        ),
    ],
)
def test_convert_to_legacy_valuespec(
    new_valuespec: api_v1.ValueSpec, expected: legacy_valuespecs.ValueSpec
) -> None:
    _compare_specs(_convert_to_legacy_valuespec(new_valuespec, _), expected)


@pytest.mark.parametrize(
    ["new_functionality", "new_topic", "expected"],
    [
        pytest.param(
            api_v1.Functionality.MONITORING_CONFIGURATION,
            api_v1.Topic.APPLICATIONS,
            wato.RulespecGroupCheckParametersApplications,
            id="CheckParametersApplications",
        ),
    ],
)
def test_convert_to_legacy_rulespec_group(
    new_functionality: api_v1.Functionality,
    new_topic: api_v1.Topic,
    expected: type[watolib.rulespecs.RulespecSubGroup],
) -> None:
    assert _convert_to_legacy_rulespec_group(new_functionality, new_topic) == expected


@pytest.mark.parametrize(
    ["new_rulespec", "expected"],
    [
        pytest.param(
            api_v1.CheckParameterRuleSpecWithItem(
                name="test_rulespec",
                title=api_v1.Localizable("rulespec title"),
                topic=api_v1.Topic.APPLICATIONS,
                item=api_v1.TextInput(title=api_v1.Localizable("item title")),
                value_spec=partial(
                    api_v1.Dictionary,
                    elements={
                        "key": api_v1.DictElement(
                            api_v1.MonitoringState(title=api_v1.Localizable("valuespec title"))
                        ),
                    },
                ),
                help_text=api_v1.Localizable("help text"),
            ),
            legacy_rulespecs.CheckParameterRulespecWithItem(
                check_group_name="test_rulespec",
                group=wato.RulespecGroupCheckParametersApplications,
                title=lambda: _("rulespec title"),
                item_spec=lambda: legacy_valuespecs.TextInput(title=_("item title")),
                parameter_valuespec=lambda: legacy_valuespecs.Dictionary(
                    elements=[
                        ("key", legacy_valuespecs.MonitoringState(title=_("valuespec title")))
                    ],
                ),
                match_type="dict",
                create_manual_check=False,  # TODO adapt when enforced services are created
            ),
            id="CheckParameterRuleSpecWithItem",
        )
    ],
)
def test_convert_to_legacy_rulespec(
    new_rulespec: api_v1.RuleSpec, expected: legacy_rulespecs.Rulespec
) -> None:
    _compare_specs(convert_to_legacy_rulespec(new_rulespec, _), expected)


def _compare_specs(actual: object, expected: object) -> None:
    ignored_attrs = {"__orig_class__"}

    if isinstance(expected, Sequence) and not isinstance(expected, str):
        assert isinstance(actual, Sequence) and not isinstance(actual, str)
        assert len(actual) == len(expected)
        for actual_elem, expected_elem in zip(actual, expected):
            _compare_specs(actual_elem, expected_elem)
        return

    if not hasattr(expected, "__dict__"):
        assert actual == expected
        return

    expected_keys = expected.__dict__.keys() - ignored_attrs
    actual_keys = actual.__dict__.keys() - ignored_attrs
    assert expected_keys == actual_keys

    for attr, expected_value in expected.__dict__.items():
        if attr in ignored_attrs:
            continue
        actual_value = getattr(actual, attr)
        if attr in ["_custom_validate", "_validate"]:
            # testing the equality of the validation in a generic way seems very difficult
            #  check that the field was set during conversion and test behavior separately
            assert (actual_value is not None) is (expected_value is not None)
            continue
        if not callable(expected_value):
            _compare_specs(actual_value, expected_value)
            continue

        try:
            _compare_specs(actual_value(), expected_value())
        except TypeError:  # deal with valuespec constructors
            assert actual_value == expected_value


@pytest.mark.parametrize(
    "input_value",
    [
        pytest.param("admin", id="custom validation"),
        pytest.param("", id="empty validation"),
        pytest.param(".", id="regex validation"),
    ],
)
def test_convert_validation(input_value: str) -> None:
    converted_spec = _convert_to_legacy_valuespec(
        api_v1.TextInput(custom_validate=_v1_custom_text_validate), _
    )

    expected_spec = legacy_valuespecs.TextInput(
        validate=_legacy_custom_text_validate,
        regex=r"^[^.\r\n]+$",
        regex_error=_("No dot allowed"),
        allow_empty=False,
        empty_text=_("Fill this"),
    )

    test_args = (input_value, "var_prefix")
    with pytest.raises(MKUserError) as expected_error:
        expected_spec.validate_value(*test_args)

    with pytest.raises(MKUserError) as actual_error:
        converted_spec.validate_value(*test_args)

    assert actual_error.value.args == expected_error.value.args
    assert actual_error.value.message == expected_error.value.message
    assert actual_error.value.varname == expected_error.value.varname
