#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.form_specs.vue.visitors import (
    DataOrigin,
    get_visitor,
    SingleChoiceVisitor,
    VisitorOptions,
)

from cmk.rulesets.v1 import Message, Title
from cmk.rulesets.v1.form_specs import SingleChoice, SingleChoiceElement
from cmk.rulesets.v1.form_specs.validators import ValidationError


def nonstop_complainer(name: str) -> None:
    raise ValidationError(Message("Ugh, tests, am I right?"))


def test_validate_returns_frontend_representation_of_replacement_value() -> None:
    # GIVEN
    spec = SingleChoice(
        elements=[SingleChoiceElement(name="foo", title=Title("Foo"))],
        custom_validate=[nonstop_complainer],
    )
    visitor = get_visitor(spec, VisitorOptions(data_origin=DataOrigin.DISK))

    # WHEN
    validation = visitor.validate("foo")

    # THEN
    assert validation
    assert validation[0].invalid_value == SingleChoiceVisitor.option_id("foo")
