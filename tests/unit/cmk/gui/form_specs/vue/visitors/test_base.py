#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import override

import cmk.shared_typing.vue_formspec_components as VueTypes
from cmk.gui.form_specs.vue import DefaultValue, IncomingData, InvalidValue, RawDiskData
from cmk.gui.form_specs.vue._visitor_base import FormSpecVisitor
from cmk.rulesets.v1 import Message
from cmk.rulesets.v1.form_specs import String
from cmk.rulesets.v1.form_specs.validators import ValidationError


def nonstop_complainer(name: str) -> None:
    raise ValidationError(Message("Ugh, tests, am I right?"))


class RandomSentinel: ...


_ParsedValue = str
_FallbackModel = RandomSentinel


class DummyVisitor(FormSpecVisitor[String, _ParsedValue, _FallbackModel]):
    @override
    def _parse_value(self, raw_value: IncomingData) -> _ParsedValue | InvalidValue[_FallbackModel]:
        if isinstance(raw_value, DefaultValue):
            return "this isn't under test"

        if raw_value.value == "error":
            return InvalidValue(
                reason="This is a dummy error",
                fallback_value=RandomSentinel(),
            )

        return str(raw_value.value)

    @override
    def _to_vue(
        self, parsed_value: _ParsedValue | InvalidValue[_FallbackModel]
    ) -> tuple[VueTypes.String, object]:
        frontend_value = (
            "frontend_fallback"
            if isinstance(parsed_value, InvalidValue)
            else f"frontend_{parsed_value}"
        )

        return (
            VueTypes.String(
                title="Dummy String",
                help="Dummy Help",
                label=None,
                validators=[],
                input_hint=None,
                field_size=VueTypes.StringFieldSize.SMALL,
                autocompleter=None,
            ),
            frontend_value,
        )

    @override
    def _to_disk(self, parsed_value: _ParsedValue) -> object:
        return parsed_value


def test_validate_returns_frontend_representation_of_replacement_value() -> None:
    # GIVEN
    visitor = DummyVisitor(String())

    # WHEN
    validation = visitor.validate(RawDiskData("error"))

    # THEN
    assert validation
    assert validation[0].replacement_value == "frontend_fallback"


def test_validate_returns_frontend_representation_of_parsed_value() -> None:
    # GIVEN
    visitor = DummyVisitor(
        String(custom_validate=[nonstop_complainer]),
    )

    # WHEN
    validation = visitor.validate(RawDiskData("foo"))

    # THEN
    assert validation
    assert validation[0].replacement_value == "frontend_foo"
