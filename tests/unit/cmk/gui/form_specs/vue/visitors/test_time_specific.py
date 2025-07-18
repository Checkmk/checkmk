#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.form_specs.private import TimeSpecific
from cmk.gui.form_specs.vue import DEFAULT_VALUE, get_visitor, RawDiskData
from cmk.gui.form_specs.vue.visitors import (
    SingleChoiceVisitor,
)
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Integer,
)
from cmk.shared_typing import vue_formspec_components as shared_type_defs


def time_specific_int_spec() -> TimeSpecific:
    return TimeSpecific(
        parameter_form=Integer(title=Title("Parameter Form"), prefill=DefaultValue(45))
    )


def time_specific_dict_spec() -> TimeSpecific:
    return TimeSpecific(
        parameter_form=Dictionary(
            title=Title("Parameter Form"),
            elements={"foo": DictElement(parameter_form=Integer(prefill=DefaultValue(45)))},
        )
    )


def test_time_specific_default_value_with_int() -> None:
    visitor = get_visitor(time_specific_int_spec())

    _spec, value = visitor.to_vue(DEFAULT_VALUE)
    assert isinstance(value, int)


def test_time_specific_default_value_with_dict() -> None:
    visitor = get_visitor(time_specific_dict_spec())

    _spec, value = visitor.to_vue(DEFAULT_VALUE)
    assert isinstance(value, dict)
    assert shared_type_defs.TimeSpecific.time_specific_values_key not in value
    assert shared_type_defs.TimeSpecific.default_value_key not in value


def test_time_specific_wrapping() -> None:
    visitor = get_visitor(time_specific_dict_spec())

    _spec, frontend_value = visitor.to_vue(
        RawDiskData(
            {
                "tp_default_value": {"foo": 25},
                "tp_values": [("24X7", {"foo": 25})],
            }
        )
    )
    assert frontend_value == {
        "tp_default_value": {"foo": 25},
        "tp_values": [
            {"timeperiod": SingleChoiceVisitor.option_id("24X7"), "parameters": {"foo": 25}}
        ],
    }


def test_time_specific_wrapping_error() -> None:
    visitor = get_visitor(
        time_specific_dict_spec(),
    )

    validation_messages = visitor.validate(
        RawDiskData(
            {"tp_default_value": {"foo": 25}, "tp_values": [("24X7", {"bar": 25, "baff": 24})]}
        )
    )
    assert len(validation_messages) == 1
    assert validation_messages[0].replacement_value == {}

    _spec, frontend_value = visitor.to_vue(
        RawDiskData({"tp_default_value": {"foo": 25}, "tp_values": [("24X7", {"bar": 25})]})
    )
    assert frontend_value == {
        "tp_default_value": {"foo": 25},
        "tp_values": [{"timeperiod": SingleChoiceVisitor.option_id("24X7"), "parameters": {}}],
    }
