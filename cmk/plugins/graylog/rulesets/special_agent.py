#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
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
from cmk.rulesets.v1.form_specs._basic import Integer, SingleChoiceElement, TimeMagnitude, TimeSpan
from cmk.rulesets.v1.form_specs._composed import MultipleChoice, MultipleChoiceElement
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def parameter_form() -> Dictionary:
    return Dictionary(
        title=Title("Graylog"),
        help_text=Help("Requests node, cluster and indice data from a Graylog instance."),
        elements={
            "instance": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Graylog instance to query"),
                    help_text=Help(
                        "Use this option to set which instance should be "
                        "checked by the special agent. Please add the "
                        "host name here, e.g. my_graylog.com."
                    ),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
            ),
            "user": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Username"),
                    help_text=Help(
                        "The username that should be used for accessing the "
                        "Graylog API. Has to have read permissions at least."
                    ),
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
                        SingleChoiceElement("http", title=Title("HTTP")),
                        SingleChoiceElement("https", title=Title("HTTPS")),
                    ],
                    prefill=DefaultValue("https"),
                ),
            ),
            "port": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("Port"),
                    help_text=Help(
                        "Use this option to query a port which is different from standard port 443."
                    ),
                    prefill=DefaultValue(443),
                    custom_validate=[
                        validators.NetworkPort(),
                    ],
                ),
            ),
            "since": DictElement(
                required=True,
                parameter_form=TimeSpan(
                    title=Title("Time for coverage of failures"),
                    help_text=Help(
                        "If you choose to query for failed index operations, use "
                        "this option to set the timeframe in which failures "
                        "should be covered. The check will output the total "
                        "number of failures and the number of failures in this "
                        "given timeframe."
                    ),
                    prefill=DefaultValue(1800),
                    displayed_magnitudes=[
                        TimeMagnitude.SECOND,
                        TimeMagnitude.MINUTE,
                        TimeMagnitude.HOUR,
                        TimeMagnitude.DAY,
                    ],
                    migrate=_migrate_to_float,
                ),
            ),
            "source_since": DictElement(
                required=False,
                parameter_form=TimeSpan(
                    title=Title("Time for coverage of sources"),
                    help_text=Help(
                        "If you choose to query for the total number of messages in a specific timeframe, use "
                        "this option to set the timeframe. The check will output the total number of messages received "
                        "in this given timeframe."
                    ),
                    prefill=DefaultValue(1800),
                    displayed_magnitudes=[
                        TimeMagnitude.SECOND,
                        TimeMagnitude.MINUTE,
                        TimeMagnitude.HOUR,
                        TimeMagnitude.DAY,
                    ],
                    migrate=_migrate_to_float,
                ),
            ),
            "alerts_since": DictElement(
                required=False,
                parameter_form=TimeSpan(
                    title=Title("Time for coverage of alerts"),
                    help_text=Help(
                        "If you choose to query for the total number of alerts in a specific timeframe, use "
                        "this option to set the timeframe. The check will output the total number of alerts received "
                        "in this given timeframe."
                    ),
                    prefill=DefaultValue(1800),
                    displayed_magnitudes=[
                        TimeMagnitude.SECOND,
                        TimeMagnitude.MINUTE,
                        TimeMagnitude.HOUR,
                        TimeMagnitude.DAY,
                    ],
                    migrate=_migrate_to_float,
                ),
            ),
            "events_since": DictElement(
                required=False,
                parameter_form=TimeSpan(
                    title=Title("Time for coverage of events"),
                    help_text=Help(
                        "If you choose to query for the total number of events in a specific timeframe, use "
                        "this option to set the timeframe. The check will output the total number of events received "
                        "in this given timeframe."
                    ),
                    prefill=DefaultValue(1800),
                    displayed_magnitudes=[
                        TimeMagnitude.SECOND,
                        TimeMagnitude.MINUTE,
                        TimeMagnitude.HOUR,
                        TimeMagnitude.DAY,
                    ],
                    migrate=_migrate_to_float,
                ),
            ),
            "sections": DictElement(
                required=True,
                parameter_form=MultipleChoice(
                    title=Title("Information to query"),
                    help_text=Help("Defines what information to query."),
                    elements=[
                        MultipleChoiceElement(name="alerts", title=Title("Alarms")),
                        MultipleChoiceElement(
                            name="cluster_stats", title=Title("Cluster statistics")
                        ),
                        MultipleChoiceElement(
                            name="cluster_traffic", title=Title("Cluster traffic statistics")
                        ),
                        MultipleChoiceElement(
                            name="failures", title=Title("Failed index operations")
                        ),
                        MultipleChoiceElement(name="jvm", title=Title("JVM heap size")),
                        MultipleChoiceElement(name="license", title=Title("License state")),
                        MultipleChoiceElement(name="messages", title=Title("Message count")),
                        MultipleChoiceElement(name="nodes", title=Title("Nodes")),
                        MultipleChoiceElement(name="sidecars", title=Title("Sidecars")),
                        MultipleChoiceElement(name="sources", title=Title("Sources")),
                        MultipleChoiceElement(name="streams", title=Title("Streams")),
                        MultipleChoiceElement(name="events", title=Title("Events")),
                    ],
                    prefill=DefaultValue(
                        [
                            "alerts",
                            "cluster_stats",
                            "cluster_traffic",
                            "failures",
                            "jvm",
                            "license",
                            "messages",
                            "nodes",
                            "sidecars",
                            "sources",
                            "streams",
                            "events",
                        ]
                    ),
                ),
            ),
            "display_node_details": DictElement(
                required=True,
                parameter_form=SingleChoice(
                    title=Title("Display node details on"),
                    help_text=Help(
                        "The node details can be displayed either on the "
                        "queried host or the Graylog node."
                    ),
                    elements=[
                        SingleChoiceElement("host", title=Title("The queried Graylog host")),
                        SingleChoiceElement("node", title=Title("The Graylog node")),
                    ],
                    prefill=DefaultValue("host"),
                ),
            ),
            "display_sidecar_details": DictElement(
                required=True,
                parameter_form=SingleChoice(
                    title=Title("Display sidecar details on"),
                    help_text=Help(
                        "The sidecar details can be displayed either on the "
                        "queried host or the sidecar host."
                    ),
                    elements=[
                        SingleChoiceElement("host", title=Title("The queried Graylog host")),
                        SingleChoiceElement("sidecar", title=Title("The sidecar host")),
                    ],
                    prefill=DefaultValue("host"),
                ),
            ),
            "display_source_details": DictElement(
                required=True,
                parameter_form=SingleChoice(
                    title=Title("Display source details on"),
                    help_text=Help(
                        "The source details can be displayed either on the "
                        "queried host or the source host."
                    ),
                    elements=[
                        SingleChoiceElement("host", title=Title("The queried Graylog host")),
                        SingleChoiceElement("source", title=Title("The source host")),
                    ],
                    prefill=DefaultValue("host"),
                ),
            ),
        },
    )


rule_spec_special_agent_graylog = SpecialAgent(
    name="graylog",
    title=Title("Graylog"),
    topic=Topic.GENERAL,
    parameter_form=parameter_form,
)


def _migrate_to_float(value: object) -> float:
    match value:
        case int(value) | float(value):
            return float(value)
    raise ValueError(value)
