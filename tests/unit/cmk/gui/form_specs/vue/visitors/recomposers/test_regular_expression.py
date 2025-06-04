#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.gui.form_specs.vue.visitors import DataOrigin, get_visitor, VisitorOptions

from cmk.rulesets.v1 import Message
from cmk.rulesets.v1.form_specs import MatchingScope, RegularExpression
from cmk.rulesets.v1.form_specs.validators import ValidationError


@pytest.mark.parametrize(
    "value",
    [
        ".*",
        "",  # Acceptable at the moment
    ],
)
def test_validate_ok_regex(request_context: None, value: str) -> None:
    form_spec = RegularExpression(predefined_help_text=MatchingScope.FULL)
    visitor = get_visitor(form_spec, options=VisitorOptions(data_origin=DataOrigin.DISK))

    errors = visitor.validate(value)

    assert not errors


def test_global_flags_in_middle_is_invalid(request_context: None) -> None:
    form_spec = RegularExpression(predefined_help_text=MatchingScope.FULL)
    visitor = get_visitor(form_spec, options=VisitorOptions(data_origin=DataOrigin.DISK))
    global_flags_in_middle_regex = "~(?i)^(?!.*\b(deprecated|dev|lab|sysprepped|Omnistack)\b).*$"

    errors = visitor.validate(global_flags_in_middle_regex)

    assert len(errors) == 1
    assert errors[0].message.startswith("Invalid regular expression:")


def test_syntax_error_is_invalid(request_context: None) -> None:
    form_spec = RegularExpression(predefined_help_text=MatchingScope.FULL)
    visitor = get_visitor(form_spec, options=VisitorOptions(data_origin=DataOrigin.DISK))
    syntax_error_regex = "^(.*server.*}$"

    errors = visitor.validate(syntax_error_regex)

    assert len(errors) == 1
    assert errors[0].message.startswith("Invalid regular expression:")


def test_custom_validate_is_applied(request_context: None) -> None:
    def custom_validator(value: str) -> str:
        raise ValidationError(Message("Custom validation failed"))

    form_spec = RegularExpression(
        predefined_help_text=MatchingScope.FULL, custom_validate=[custom_validator]
    )
    visitor = get_visitor(form_spec, options=VisitorOptions(data_origin=DataOrigin.DISK))

    errors = visitor.validate("foo")

    assert len(errors) == 1
    assert errors[0].message == "Custom validation failed"
