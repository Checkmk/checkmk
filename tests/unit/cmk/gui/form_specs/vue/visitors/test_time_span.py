#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Sequence

from cmk.gui.form_specs.vue import get_visitor, RawFrontendData
from cmk.rulesets.v1 import Help, Label, Message, Title
from cmk.rulesets.v1.form_specs import TimeMagnitude, TimeSpan
from cmk.rulesets.v1.form_specs.validators import NumberInRange
from cmk.shared_typing import vue_formspec_components as shared_type_defs


def _get_time_span(custom_validate: Sequence[Callable[[float], object]]) -> TimeSpan:
    return TimeSpan(
        title=Title("time_span title"),
        help_text=Help("time_span help"),
        label=Label("label"),
        displayed_magnitudes=[TimeMagnitude.HOUR],
        custom_validate=custom_validate,
    )


def test_time_span_validator() -> None:
    time_span_spec = _get_time_span(
        [
            NumberInRange(
                # value should be between 1 hour and 1 week
                min_value=1 * 60 * 60,
                max_value=7 * 24 * 60 * 60,
            )
        ]
    )
    visitor = get_visitor(time_span_spec)

    assert visitor.validate(RawFrontendData(1)) == [
        shared_type_defs.ValidationMessage(
            location=[],
            message="Allowed values range from 1 hours to 7 days.",
            replacement_value=1.0,
        ),
    ]


def test_time_span_validator_custom_message() -> None:
    time_span_spec = _get_time_span(
        [
            NumberInRange(
                # value should be greater than 1 hour
                min_value=1 * 60 * 60,
                error_msg=Message(
                    "XXX this error message should be visible in validation output but will be overwritten."
                ),
            )
        ]
    )
    visitor = get_visitor(time_span_spec)

    assert visitor.validate(RawFrontendData(1)) == [
        shared_type_defs.ValidationMessage(
            location=[],
            # custom error_msg from above is overwritten :-(
            message="The minimum allowed value is 1 hours.",
            replacement_value=1.0,
        ),
    ]
