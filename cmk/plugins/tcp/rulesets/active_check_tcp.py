#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    DataSize,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    IECMagnitude,
    InputHint,
    Integer,
    LevelDirection,
    List,
    migrate_to_float_simple_levels,
    SimpleLevels,
    SingleChoice,
    SingleChoiceElement,
    String,
    TimeMagnitude,
    TimeSpan,
    validators,
)
from cmk.rulesets.v1.rule_specs import ActiveCheck, Topic

_DAY = 86400


def _migrate_to_float(v: object) -> float:
    """
    >>> _migrate_to_float(1)
    1.0
    >>> _migrate_to_float(1.0)
    1.0
    """
    match v:
        case int() | float():
            return float(v)
    raise ValueError(f"Expected int or float, got {type(v)}")


def _make_parameter_form() -> Dictionary:
    return Dictionary(
        title=Title("Check TCP port connection"),
        help_text=Help(
            "This check tests the connection to a TCP port. It uses "
            "<tt>check_tcp</tt> from the standard Nagios plug-ins."
        ),
        elements={
            "port": DictElement(
                parameter_form=Integer(
                    title=Title("TCP Port"), custom_validate=(validators.NetworkPort(),)
                ),
                required=True,
            ),
            "svc_description": DictElement(
                parameter_form=String(
                    title=Title("Service name"),
                    custom_validate=(validators.LengthInRange(1, None),),
                    help_text=Help(
                        "Here you can specify a service name. "
                        "If this parameter is not set, the service is named <tt>TCP Port [PORT NUMBER]</tt>"
                    ),
                ),
            ),
            "hostname": DictElement(
                parameter_form=String(
                    title=Title("DNS host name"),
                    custom_validate=(validators.LengthInRange(1, None),),
                    help_text=Help(
                        "If you specify a host name here, then a dynamic DNS lookup "
                        "will be done instead of using the IP address of the host "
                        "as configured in your host properties."
                    ),
                    macro_support=True,
                ),
            ),
            "response_time": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Expected response time"),
                    level_direction=LevelDirection.UPPER,
                    migrate=lambda v: migrate_to_float_simple_levels(v, 0.001),
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=(TimeMagnitude.MILLISECOND,),
                    ),
                    prefill_fixed_levels=InputHint((0.1, 0.2)),
                ),
            ),
            "timeout": DictElement(
                parameter_form=TimeSpan(
                    title=Title("Seconds before connection times out"),
                    displayed_magnitudes=(TimeMagnitude.SECOND,),
                    prefill=DefaultValue(10.0),
                    migrate=_migrate_to_float,
                )
            ),
            "refuse_state": DictElement(
                parameter_form=SingleChoice(
                    title=Title("State for connection refusal"),
                    elements=(
                        SingleChoiceElement("crit", Title("CRITICAL")),
                        SingleChoiceElement("warn", Title("WARNING")),
                        SingleChoiceElement("ok", Title("OK")),
                    ),
                ),
            ),
            "send_string": DictElement(
                parameter_form=String(
                    title=Title("String to send"),
                )
            ),
            "escape_send_string": DictElement(
                parameter_form=FixedValue(
                    value=True,
                    title=Title(
                        "Expand <tt>\\n</tt>, <tt>\\r</tt> and <tt>\\t</tt> in the sent string"
                    ),
                    label=Label("expand escapes"),
                )
            ),
            "expect": DictElement(
                parameter_form=List(
                    title=Title("Strings to expect in response"),
                    element_template=String(),
                ),
            ),
            "expect_all": DictElement(
                parameter_form=FixedValue(
                    value=True,
                    title=Title("Expect <b>all</b> of those strings in the response"),
                    label=Label("expect all"),
                )
            ),
            "jail": DictElement(
                parameter_form=FixedValue(
                    value=True,
                    title=Title("Hide response from socket"),
                    help_text=Help(
                        "As soon as you configure expected strings in "
                        "the response the check will output the response - "
                        "as long as you do not hide it with this option"
                    ),
                    label=Label("hide response"),
                ),
            ),
            "mismatch_state": DictElement(
                parameter_form=SingleChoice(
                    title=Title("State for expected string mismatch"),
                    elements=(
                        SingleChoiceElement("crit", Title("CRITICAL")),
                        SingleChoiceElement("warn", Title("WARNING")),
                        SingleChoiceElement("ok", Title("OK")),
                    ),
                ),
            ),
            "delay": DictElement(
                parameter_form=TimeSpan(
                    title=Title("Seconds to wait before polling"),
                    help_text=Help(
                        "Seconds to wait between sending string and polling for response"
                    ),
                    displayed_magnitudes=(TimeMagnitude.SECOND,),
                    prefill=DefaultValue(0.0),
                    migrate=_migrate_to_float,
                ),
            ),
            "maxbytes": DictElement(
                parameter_form=DataSize(
                    title=Title("Maximum number of bytes to receive"),
                    displayed_magnitudes=(IECMagnitude.KIBI,),
                    help_text=Help(
                        "Close connection once more than this number of "
                        "bytes are received. Per default the number of "
                        "read bytes is not limited. This setting is only "
                        "used if you expect strings in the response."
                    ),
                    prefill=DefaultValue(1024),
                ),
            ),
            "ssl": DictElement(
                parameter_form=FixedValue(
                    value=True,
                    title=Title("Use SSL for the connection"),
                ),
            ),
            "cert_days": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("SSL certificate validation"),
                    help_text=Help("Minimum number of days a certificate has to be valid"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=TimeSpan(displayed_magnitudes=(TimeMagnitude.DAY,)),
                    prefill_fixed_levels=InputHint((7 * _DAY, 2 * _DAY)),
                    migrate=lambda v: migrate_to_float_simple_levels(v, _DAY),
                ),
            ),
            "quit_string": DictElement(
                parameter_form=String(
                    title=Title("Final string to send"),
                    help_text=Help(
                        "String to send server to initiate a clean close of the connection"
                    ),
                ),
            ),
        },
    )


rule_spec_tcp = ActiveCheck(
    name="tcp",
    title=Title("Check TCP port connection"),
    parameter_form=_make_parameter_form,
    topic=Topic.NETWORKING,
)
