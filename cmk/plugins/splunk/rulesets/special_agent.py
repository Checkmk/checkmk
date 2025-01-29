#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    migrate_to_password,
    Password,
    SingleChoice,
    String,
    validators,
)
from cmk.rulesets.v1.form_specs._basic import Integer, SingleChoiceElement
from cmk.rulesets.v1.form_specs._composed import MultipleChoice, MultipleChoiceElement
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _parameter_form() -> Dictionary:
    return Dictionary(
        title=Title("Splunk"),
        help_text=Help("Requests data from a Splunk instance."),
        # optional_keys=["instance", "port"],
        elements={
            "instance": DictElement(
                required=False,
                parameter_form=String(
                    title=Title("Splunk instance to query."),
                    help_text=Help(
                        "Use this option to set which host should be checked by the special agent."
                    ),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
            ),
            "user": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Username"),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
            ),
            "password": DictElement(
                required=True,
                parameter_form=Password(
                    title=Title("Password of the user"),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                    migrate=migrate_to_password,
                ),
            ),
            "protocol": DictElement(
                required=True,
                parameter_form=SingleChoice(
                    title=Title("Protocol"),
                    elements=[
                        SingleChoiceElement(name="http", title=Title("HTTP")),
                        SingleChoiceElement(name="https", title=Title("HTTPS")),
                    ],
                    prefill=DefaultValue("https"),
                ),
            ),
            "port": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("Port"),
                    help_text=Help(
                        "Use this option to query a port which is different from standard port 8089."
                    ),
                    custom_validate=(validators.NetworkPort(),),
                    prefill=DefaultValue(8089),
                ),
            ),
            "infos": DictElement(
                required=True,
                parameter_form=MultipleChoice(
                    title=Title("Informations to query"),
                    help_text=Help(
                        "Defines what information to query. You can "
                        "choose to query license state and usage, Splunk "
                        "system messages, Splunk jobs, shown in the job "
                        "menu within Splunk. You can also query for "
                        "component health and fired alerts."
                    ),
                    elements=[
                        MultipleChoiceElement(name="license_state", title=Title("Licence state")),
                        MultipleChoiceElement(name="license_usage", title=Title("Licence usage")),
                        MultipleChoiceElement(name="system_msg", title=Title("System messages")),
                        MultipleChoiceElement(name="jobs", title=Title("Jobs")),
                        MultipleChoiceElement(name="health", title=Title("Health")),
                        MultipleChoiceElement(name="alerts", title=Title("Alerts")),
                    ],
                    prefill=DefaultValue(
                        [
                            "license_state",
                            "license_usage",
                            "system_msg",
                            "jobs",
                            "health",
                            "alerts",
                        ]
                    ),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
            ),
        },
    )


rule_spec_special_agent_splunk = SpecialAgent(
    name="splunk",
    title=Title("Splunk"),
    topic=Topic.GENERAL,
    parameter_form=_parameter_form,
)
