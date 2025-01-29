#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    FieldSize,
    Integer,
    migrate_to_password,
    MultipleChoice,
    MultipleChoiceElement,
    Password,
    SingleChoice,
    SingleChoiceElement,
    String,
    validators,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _form_spec_special_agents_rabbitmq():
    return Dictionary(
        title=Title("RabbitMQ"),
        help_text=Help(
            "Request data from a RabbitMQ instance."
            " This special agent queries the HTTP API provided by"
            " RabbitMQs 'Management Plugin'. You need to enable this"
            " plugin in your RabbitMQ instance."
        ),
        elements={
            "instance": DictElement(
                required=False,
                parameter_form=String(
                    title=Title("RabbitMQ instance to query"),
                    field_size=FieldSize.MEDIUM,
                    custom_validate=(validators.LengthInRange(min_value=1),),
                    help_text=Help(
                        "Use this option to set which instance should be "
                        "checked by the special agent. Please add the "
                        "host name here, e.g. my_rabbitmq.com. If not set, the "
                        "assigned host is used as instance."
                    ),
                    macro_support=True,
                ),
            ),
            "user": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Username"),
                    help_text=Help(
                        "The username that should be used for accessing the RabbitMQ API."
                    ),
                    field_size=FieldSize.MEDIUM,
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
                    prefill=DefaultValue(15672),
                    help_text=Help("The port that is used for the api call."),
                    custom_validate=(validators.NetworkPort(),),
                ),
            ),
            "sections": DictElement(
                required=True,
                parameter_form=MultipleChoice(
                    title=Title("Informations to query"),
                    help_text=Help(
                        "Defines what information to query. You can choose "
                        "between the cluster, nodes, vhosts and queues."
                    ),
                    elements=[
                        MultipleChoiceElement(name="cluster", title=Title("Clusterwide")),
                        MultipleChoiceElement(name="nodes", title=Title("Nodes")),
                        MultipleChoiceElement(name="vhosts", title=Title("Vhosts")),
                        MultipleChoiceElement(name="queues", title=Title("Queues")),
                    ],
                    prefill=DefaultValue(["cluster", "nodes", "vhosts", "queues"]),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
            ),
        },
    )


rule_spec_special_agent_rabbitmq = SpecialAgent(
    name="rabbitmq",
    title=Title("RabbitMQ"),
    topic=Topic.APPLICATIONS,
    parameter_form=_form_spec_special_agents_rabbitmq,
)
