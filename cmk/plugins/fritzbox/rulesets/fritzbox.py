#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.rulesets.v1 import form_specs, Help, rule_specs, Title


def _formspec_fritzbox():
    return form_specs.Dictionary(
        help_text=Help(
            "This rule selects the Fritz!Box agent, which uses UPNP to gather information "
            "about configuration and connection status information."
        ),
        elements={
            "timeout": form_specs.DictElement(
                parameter_form=form_specs.TimeSpan(
                    title=Title("Connection timeout"),
                    displayed_magnitudes=[form_specs.TimeMagnitude.SECOND],
                    help_text=Help(
                        "The network timeout in seconds when communicating via UPNP. "
                        "The default is 10 seconds. Please note that this "
                        "is not a total timeout, instead it is applied to each API call."
                    ),
                    prefill=form_specs.DefaultValue(10.0),
                    custom_validate=(form_specs.validators.NumberInRange(1.0, None),),
                    migrate=float,  # type: ignore[arg-type]
                ),
            ),
        },
    )


rule_spec_fritzbox = rule_specs.SpecialAgent(
    name="fritzbox",
    title=Title("Fritz!Box Devices"),
    topic=rule_specs.Topic.NETWORKING,
    parameter_form=_formspec_fritzbox,
)
