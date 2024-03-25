#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    DefaultValue,
    DictElement,
    Dictionary,
    Integer,
    List,
    migrate_to_password,
    Password,
    String,
    validators,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _form_special_agents_3par() -> Dictionary:
    return Dictionary(
        title=Title("3PAR Configuration"),
        elements={
            "user": DictElement(
                parameter_form=String(
                    title=Title("Username"),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
                required=True,
            ),
            "password": DictElement(
                parameter_form=Password(
                    title=Title("Password"),
                    migrate=migrate_to_password,
                ),
                required=True,
            ),
            "port": DictElement(
                parameter_form=Integer(
                    title=Title("TCP port number"),
                    help_text=Help("Port number that 3par is listening on. The default is 8080."),
                    custom_validate=(validators.NetworkPort(),),
                    prefill=DefaultValue(8080),
                ),
                required=True,
            ),
            "verify_cert": DictElement(
                parameter_form=BooleanChoice(
                    label=Label("SSL certificate verification"),
                ),
                required=True,
            ),
            "values": DictElement(
                parameter_form=List(
                    element_template=String(),
                    title=Title("Values to fetch"),
                    help_text=Help(
                        "Possible values are the following: cpgs, volumes, hosts, capacity, "
                        "system, ports, remotecopy, hostsets, volumesets, vluns, flashcache, "
                        "users, roles, qos.\n"
                        "If you do not specify any value the first seven are used as default."
                    ),
                )
            ),
        },
    )


rule_spec_three_par = SpecialAgent(
    name="three_par",
    title=Title("3PAR Configuration"),
    topic=Topic.SERVER_HARDWARE,
    parameter_form=_form_special_agents_3par,
)
