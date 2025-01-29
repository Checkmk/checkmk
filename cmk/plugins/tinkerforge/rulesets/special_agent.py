#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Integer,
    String,
    validators,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _parameter_form() -> Dictionary:
    return Dictionary(
        elements={
            "port": DictElement(
                parameter_form=Integer(
                    title=Title("TCP port number"),
                    help_text=Help(
                        "Port number that AppDynamics is listening on. The default is 8090."
                    ),
                    custom_validate=(validators.NetworkPort(),),
                    prefill=DefaultValue(4223),
                ),
            ),
            "segment_display_uid": DictElement(
                parameter_form=String(
                    title=Title("7-segment display uid"),
                    help_text=Help(
                        "This is the uid of the sensor you want to display in the 7-segment display, "
                        "not the uid of the display itself. There is currently no support for "
                        "controling multiple displays."
                    ),
                ),
            ),
            "segment_display_brightness": DictElement(
                parameter_form=Integer(
                    title=Title("7-segment display brightness"),
                    custom_validate=(validators.NumberInRange(min_value=0, max_value=7),),
                ),
            ),
        },
    )


rule_spec_special_agent_tinkerforge = SpecialAgent(
    name="tinkerforge",
    title=Title("Tinkerforge"),
    topic=Topic.SERVER_HARDWARE,
    parameter_form=_parameter_form,
)
