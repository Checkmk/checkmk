#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.user import UserId

from cmk.gui.form_specs.vue import DEFAULT_VALUE, get_visitor, RawDiskData, RawFrontendData
from cmk.gui.form_specs.vue.visitors import SingleChoiceVisitor
from cmk.gui.form_specs.vue.visitors.single_choice import NO_SELECTION

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    InvalidElementMode,
    InvalidElementValidator,
    SingleChoice,
    SingleChoiceElement,
)


def single_choice_spec(validator: InvalidElementValidator | None = None) -> SingleChoice:
    return SingleChoice(
        elements=[
            SingleChoiceElement(name="foo", title=Title("foo")),
            SingleChoiceElement(name="bar", title=Title("bar")),
            SingleChoiceElement(name="baz", title=Title("baz")),
        ],
        invalid_element_validation=validator,
    )


@pytest.mark.parametrize(
    "invalid_choice",
    [
        pytest.param(RawDiskData("wuff"), id="same data type than element name"),
        pytest.param(RawFrontendData("wuff"), id="same data type than element name"),
        pytest.param(RawDiskData(1), id="different data type than element name"),
        pytest.param(RawFrontendData(1), id="different data type than element name"),
    ],
)
def test_invalid_single_choice_validator_keep(
    request_context: None,
    patch_theme: None,
    with_user: tuple[UserId, str],
    invalid_choice: RawFrontendData | RawDiskData,
) -> None:
    single_choice = single_choice_spec(InvalidElementValidator(mode=InvalidElementMode.KEEP))
    visitor = get_visitor(single_choice)
    _vue_spec, vue_value = visitor.to_vue(invalid_choice)
    # Do not send invalid value to vue
    assert vue_value is None

    # Create validation message
    validation_messages = visitor.validate(invalid_choice)
    assert len(validation_messages) == 1
    assert validation_messages[0].replacement_value == NO_SELECTION

    # Invalid value is sent back to disk
    if isinstance(invalid_choice, RawFrontendData):
        # You can not save an invalid value in the frontend
        with pytest.raises(MKGeneralException):
            visitor.to_disk(invalid_choice)
    else:
        # If it comes from disk, it is sent back to disk
        assert visitor.to_disk(invalid_choice) == invalid_choice.value


@pytest.mark.parametrize(
    "invalid_choice",
    [
        RawDiskData("wuff"),
        RawFrontendData("wuff"),
    ],
)
def test_invalid_single_choice_validator_complain(
    request_context: None,
    patch_theme: None,
    with_user: tuple[UserId, str],
    invalid_choice: RawFrontendData | RawDiskData,
) -> None:
    single_choice = single_choice_spec(InvalidElementValidator(mode=InvalidElementMode.COMPLAIN))
    visitor = get_visitor(single_choice)
    _vue_spec, vue_value = visitor.to_vue(invalid_choice)
    # Do not send invalid value to vue
    assert vue_value is None

    # Create validation message
    validation_messages = visitor.validate(invalid_choice)
    assert len(validation_messages) == 1
    assert validation_messages[0].replacement_value == NO_SELECTION

    # Invalid value causes exception
    with pytest.raises(MKGeneralException):
        visitor.to_disk(invalid_choice)


@pytest.mark.parametrize(
    "invalid_choice",
    [
        RawDiskData("wuff"),
        RawFrontendData("wuff"),
    ],
)
def test_invalid_single_choice_validator_none(
    request_context: None,
    patch_theme: None,
    with_user: tuple[UserId, str],
    invalid_choice: RawFrontendData | RawDiskData,
) -> None:
    single_choice = single_choice_spec(None)
    visitor = get_visitor(single_choice)
    _vue_spec, vue_value = visitor.to_vue(invalid_choice)
    # Do not send invalid value to vue
    assert vue_value is None

    # Create validation message
    validation_messages = visitor.validate(invalid_choice)
    assert len(validation_messages) == 1
    assert validation_messages[0].replacement_value == NO_SELECTION

    # Invalid value causes exception
    with pytest.raises(MKGeneralException):
        visitor.to_disk(invalid_choice)


@pytest.mark.parametrize(
    "valid_choice",
    [
        RawDiskData("bar"),
        RawFrontendData(SingleChoiceVisitor.option_id("bar")),
    ],
)
def test_single_choice_valid_value(
    request_context: None,
    patch_theme: None,
    with_user: tuple[UserId, str],
    valid_choice: RawFrontendData | RawDiskData,
) -> None:
    single_choice = single_choice_spec(None)
    visitor = get_visitor(single_choice)

    vue_spec, vue_value = visitor.to_vue(valid_choice)
    assert vue_spec.type == "single_choice"
    assert vue_value == SingleChoiceVisitor.option_id("bar")

    validation_messages = visitor.validate(valid_choice)
    assert len(validation_messages) == 0

    assert visitor.to_disk(valid_choice) == "bar"


def test_default_value_roundtrip() -> None:
    single_choice = SingleChoice(
        elements=[
            SingleChoiceElement(name="foo", title=Title("foo")),
            SingleChoiceElement(name="bar", title=Title("bar")),
        ],
        prefill=DefaultValue("bar"),
    )
    visitor = get_visitor(single_choice)
    _, vue_value = visitor.to_vue(DEFAULT_VALUE)
    assert visitor.to_disk(RawFrontendData(vue_value)) == "bar"
