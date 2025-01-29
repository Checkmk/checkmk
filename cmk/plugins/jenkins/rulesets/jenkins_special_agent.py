#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Message, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Integer,
    migrate_to_password,
    MultipleChoice,
    MultipleChoiceElement,
    Password,
    SingleChoice,
    SingleChoiceElement,
    String,
)
from cmk.rulesets.v1.form_specs.validators import LengthInRange, NetworkPort, ValidationError
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _validate_sub_path(value: str) -> None:
    if value.startswith("/"):
        raise ValidationError(Message("Path is not allowed to start with '/'"))
    if any(not p for p in value.split("/")):
        raise ValidationError(Message("Path is not allowed to contain empty parts"))


def _formspec_jenkins() -> Dictionary:
    return Dictionary(
        title=Title("Jenkins connection"),
        help_text=Help("Requests data from a Jenkins instance."),
        elements={
            "instance": DictElement(
                parameter_form=String(
                    title=Title("Jenkins instance to query."),
                    help_text=Help(
                        "Use this option to set which instance should be "
                        "checked by the special agent. Please add the "
                        "host name here, e.g. my_jenkins.com."
                    ),
                    custom_validate=[
                        LengthInRange(min_value=1),
                    ],
                    macro_support=True,
                ),
                required=True,
            ),
            "path": DictElement(
                parameter_form=String(
                    title=Title("Path"),
                    help_text=Help(
                        "Add (sub) path to the URI, i.e. [proto]://[host]:[port]/[path]."
                    ),
                    custom_validate=[LengthInRange(min_value=1), _validate_sub_path],
                ),
                required=False,
            ),
            "user": DictElement(
                parameter_form=String(
                    title=Title("Username"),
                    help_text=Help(
                        "The username that should be used for accessing the "
                        "jenkins API. Has to have read permissions at least."
                    ),
                    custom_validate=[LengthInRange(min_value=1)],
                ),
                required=True,
            ),
            "password": DictElement(
                parameter_form=Password(
                    help_text=Help("The password or API key of the user."),
                    title=Title("Password of the user"),
                    custom_validate=[LengthInRange(min_value=1)],
                    migrate=migrate_to_password,
                ),
                required=True,
            ),
            "protocol": DictElement(
                parameter_form=SingleChoice(
                    title=Title("Protocol"),
                    elements=[
                        SingleChoiceElement(name="http", title=Title("HTTP")),
                        SingleChoiceElement(name="https", title=Title("HTTPS")),
                    ],
                    prefill=DefaultValue("https"),
                ),
                required=True,
            ),
            "port": DictElement(
                parameter_form=Integer(
                    title=Title("Port"),
                    help_text=Help(
                        "Use this option to query a port which is different from standard port 8080."
                    ),
                    prefill=DefaultValue(443),
                    custom_validate=[
                        NetworkPort(),
                    ],
                )
            ),
            "sections": DictElement(
                parameter_form=MultipleChoice(
                    title=Title("Monitor (min. 1)"),
                    help_text=Help(
                        "Defines what information to query. You can choose "
                        "between the instance state, job states, node states, "
                        "the job queue and system metrics."
                    ),
                    elements=[
                        MultipleChoiceElement(name="instance", title=Title("Instance state")),
                        MultipleChoiceElement(name="jobs", title=Title("Job state")),
                        MultipleChoiceElement(name="nodes", title=Title("Node state")),
                        MultipleChoiceElement(name="queue", title=Title("Queue info")),
                        MultipleChoiceElement(
                            name="system_metrics",
                            title=Title("System metrics (requires 'Metrics' plugin in Jenkins)"),
                        ),
                    ],
                    prefill=DefaultValue(["instance", "jobs", "nodes", "queue"]),
                    custom_validate=[
                        LengthInRange(
                            min_value=1,
                            error_msg=Message("Please select at least one item to monitor"),
                        ),
                    ],
                ),
                required=True,
            ),
        },
    )


rule_spec_jenkins = SpecialAgent(
    name="jenkins",
    title=Title("Jenkins"),
    topic=Topic.APPLICATIONS,
    parameter_form=_formspec_jenkins,
)
