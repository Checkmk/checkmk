#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.user import UserId

from cmk.gui.form_specs.vue.visitors import DataOrigin, get_visitor, SingleChoiceVisitor
from cmk.gui.form_specs.vue.visitors._type_defs import DEFAULT_VALUE, VisitorOptions
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


@pytest.mark.parametrize("data_origin", [DataOrigin.DISK, DataOrigin.FRONTEND])
@pytest.mark.parametrize(
    "invalid_choice",
    [
        pytest.param("wuff", id="same data type than element name"),
        pytest.param(1, id="different data type than element name"),
    ],
)
def test_invalid_single_choice_validator_keep(
    request_context: None,
    patch_theme: None,
    with_user: tuple[UserId, str],
    data_origin: DataOrigin,
    invalid_choice: object,
) -> None:
    single_choice = single_choice_spec(InvalidElementValidator(mode=InvalidElementMode.KEEP))
    visitor = get_visitor(single_choice, VisitorOptions(data_origin=data_origin))
    _vue_spec, vue_value = visitor.to_vue(invalid_choice)
    # Do not send invalid value to vue
    assert vue_value is None

    # Create validation message
    validation_messages = visitor.validate(invalid_choice)
    assert len(validation_messages) == 1
    assert validation_messages[0].replacement_value == NO_SELECTION

    # Invalid value is sent back to disk
    if data_origin == DataOrigin.FRONTEND:
        # You can not save an invalid value in the frontend
        with pytest.raises(MKGeneralException):
            visitor.to_disk(invalid_choice)
    else:
        # If it comes from disk, it is sent back to disk
        assert visitor.to_disk(invalid_choice) == invalid_choice


@pytest.mark.parametrize("data_origin", [DataOrigin.DISK, DataOrigin.FRONTEND])
def test_invalid_single_choice_validator_complain(
    request_context: None,
    patch_theme: None,
    with_user: tuple[UserId, str],
    data_origin: DataOrigin,
) -> None:
    invalid_choice = "wuff"
    single_choice = single_choice_spec(InvalidElementValidator(mode=InvalidElementMode.COMPLAIN))
    visitor = get_visitor(single_choice, VisitorOptions(data_origin=data_origin))
    _vue_spec, vue_value = visitor.to_vue(invalid_choice)
    # Do not send invalid value to vue
    assert vue_value is None

    # Create validation message
    validation_messages = visitor.validate(invalid_choice)
    assert len(validation_messages) == 1
    assert validation_messages[0].replacement_value == NO_SELECTION

    # Invalid value causes exception
    with pytest.raises(MKGeneralException):
        visitor.to_disk("wuff")


@pytest.mark.parametrize("data_origin", [DataOrigin.DISK, DataOrigin.FRONTEND])
def test_invalid_single_choice_validator_none(
    request_context: None,
    patch_theme: None,
    with_user: tuple[UserId, str],
    data_origin: DataOrigin,
) -> None:
    invalid_choice = "wuff"
    single_choice = single_choice_spec(None)
    visitor = get_visitor(single_choice, VisitorOptions(data_origin=data_origin))
    _vue_spec, vue_value = visitor.to_vue(invalid_choice)
    # Do not send invalid value to vue
    assert vue_value is None

    # Create validation message
    validation_messages = visitor.validate(invalid_choice)
    assert len(validation_messages) == 1
    assert validation_messages[0].replacement_value == NO_SELECTION

    # Invalid value causes exception
    with pytest.raises(MKGeneralException):
        visitor.to_disk("wuff")


@pytest.mark.parametrize("data_origin", [DataOrigin.DISK, DataOrigin.FRONTEND])
def test_single_choice_valid_value(
    request_context: None,
    patch_theme: None,
    with_user: tuple[UserId, str],
    data_origin: DataOrigin,
) -> None:
    valid_choice = "bar"
    single_choice = single_choice_spec(None)
    visitor = get_visitor(single_choice, VisitorOptions(data_origin=data_origin))

    if data_origin == DataOrigin.FRONTEND:
        raw_value = SingleChoiceVisitor.option_id(valid_choice)
    else:
        raw_value = valid_choice

    vue_spec, vue_value = visitor.to_vue(raw_value)
    assert vue_spec.type == "single_choice"
    assert vue_value == SingleChoiceVisitor.option_id(valid_choice)

    validation_messages = visitor.validate(raw_value)
    assert len(validation_messages) == 0

    assert visitor.to_disk(raw_value) == "bar"


@pytest.mark.parametrize("data_origin", [DataOrigin.DISK, DataOrigin.FRONTEND])
def test_default_value_from_any_origin(
    data_origin: DataOrigin,
) -> None:
    single_choice = SingleChoice(
        elements=[
            SingleChoiceElement(name="foo", title=Title("foo")),
            SingleChoiceElement(name="bar", title=Title("bar")),
        ],
        prefill=DefaultValue("bar"),
    )
    to_frontend_visitor = get_visitor(single_choice, VisitorOptions(data_origin))
    _, vue_value = to_frontend_visitor.to_vue(DEFAULT_VALUE)

    to_disk_visitor = get_visitor(single_choice, VisitorOptions(DataOrigin.FRONTEND))
    value = to_disk_visitor.to_disk(vue_value)
    assert value == "bar"
