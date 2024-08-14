#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.user import UserId

from cmk.gui.form_specs.vue.visitors import DataOrigin, get_visitor
from cmk.gui.form_specs.vue.visitors._type_defs import VisitorOptions

from cmk.ccc.exceptions import MKGeneralException
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
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
def test_invalid_single_choice_validator_keep(
    request_context: None,
    patch_theme: None,
    with_user: tuple[UserId, str],
    data_origin: DataOrigin,
) -> None:
    invalid_choice = "wuff"
    single_choice = single_choice_spec(InvalidElementValidator(mode=InvalidElementMode.KEEP))
    visitor = get_visitor(single_choice, VisitorOptions(data_origin=data_origin))
    _vue_spec, vue_value = visitor.to_vue(invalid_choice)
    # Do not send invalid value to vue
    assert vue_value == ""

    # Create validation message
    validation_messages = visitor.validate(invalid_choice)
    assert len(validation_messages) == 1
    assert validation_messages[0].invalid_value == ""

    # Invalid value is sent back to disk
    assert visitor.to_disk("wuff") == "wuff"


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
    assert vue_value == ""

    # Create validation message
    validation_messages = visitor.validate(invalid_choice)
    assert len(validation_messages) == 1
    assert validation_messages[0].invalid_value == ""

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
    assert vue_value == ""

    # Create validation message
    validation_messages = visitor.validate(invalid_choice)
    assert len(validation_messages) == 1
    assert validation_messages[0].invalid_value == ""

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
    vue_spec, vue_value = visitor.to_vue(valid_choice)

    assert vue_spec.type == "single_choice"
    assert vue_value == valid_choice

    validation_messages = visitor.validate(valid_choice)
    assert len(validation_messages) == 0

    assert visitor.to_disk("bar") == "bar"
