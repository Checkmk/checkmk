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
    migrate_to_password,
    Password,
    String,
    validators,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _parameter_form() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "This rule allows querying an AppDynamics server for information about Java applications"
            "via the AppDynamics REST API. You can configure your connection settings here."
        ),
        elements={
            "username": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("AppDynamics login user name"),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
            ),
            "password": DictElement(
                required=True,
                parameter_form=Password(
                    title=Title("AppDynamics login password"),
                    migrate=migrate_to_password,
                ),
            ),
            "application": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("AppDynamics application name"),
                    help_text=Help(
                        "This is the application name used in the URL. If you enter for example the application "
                        "name <tt>foobar</tt>, this would result in the URL being used to contact the REST API: "
                        "<tt>/controller/rest/applications/foobar/metric-data</tt>"
                    ),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
            ),
            "port": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("TCP port number"),
                    help_text=Help(
                        "Port number that AppDynamics is listening on. The default is 8090."
                    ),
                    prefill=DefaultValue(8090),
                    custom_validate=(validators.NetworkPort(),),
                ),
            ),
            "timeout": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("Connection timeout"),
                    help_text=Help(
                        "The network timeout in seconds when communicating with AppDynamics."
                        "The default is 30 seconds."
                    ),
                    prefill=DefaultValue(30),
                    unit_symbol="s",
                    custom_validate=(validators.NumberInRange(min_value=1),),
                ),
            ),
        },
    )


rule_spec_special_agent_appdynamics = SpecialAgent(
    name="appdynamics",
    title=Title("AppDynamics via REST API"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form,
)
