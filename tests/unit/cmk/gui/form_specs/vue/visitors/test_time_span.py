#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.form_specs.vue import shared_type_defs
from cmk.gui.form_specs.vue.visitors import DataOrigin, get_visitor
from cmk.gui.form_specs.vue.visitors._type_defs import VisitorOptions

from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import TimeMagnitude, TimeSpan
from cmk.rulesets.v1.form_specs.validators import NumberInRange


def test_time_span_validator() -> None:
    time_span_spec = TimeSpan(
        title=Title("time_span title"),
        help_text=Help("time_span help"),
        label=Label("label"),
        displayed_magnitudes=[TimeMagnitude.HOUR],
        custom_validate=[
            NumberInRange(
                # value should be between 1 hour and 1 week
                min_value=1 * 60 * 60,
                max_value=7 * 24 * 60 * 60,
            ),
        ],
    )

    visitor = get_visitor(time_span_spec, VisitorOptions(data_origin=DataOrigin.FRONTEND))

    validation_messages = visitor.validate(1)
    assert validation_messages == [
        shared_type_defs.ValidationMessage(
            location=[],
            message="Allowed values range from 3600 to 604800.",
            # TODO: this message is a problem:
            # The TimeSpan is configured to only show the hour field
            # but the error message reports the values in seconds.
            invalid_value=1.0,
        ),
    ]
