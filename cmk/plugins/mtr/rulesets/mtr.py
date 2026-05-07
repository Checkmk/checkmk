#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.rulesets.v1 import Help, Label, Message, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    Integer,
    List,
    SingleChoice,
    SingleChoiceElement,
    String,
    TimeMagnitude,
    TimeSpan,
    validators,
)
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic


def migrate(value: object) -> Mapping[str, object]:
    if not isinstance(value, dict):
        return {"deployment": ("do_not_deploy", None)}
    if "deployment" in value:
        return value
    return {
        "deployment": ("cached", float(value["interval"])),
        "mtr_config": value["mtr_config"],
    }


def _address_configuration() -> Dictionary:
    return Dictionary(
        elements={
            "hostname": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Destination address"),
                    help_text=Help(
                        "This will be used as service name in Checkmk."
                        " It must be a unique name per host."
                    ),
                    custom_validate=(
                        validators.LengthInRange(min_value=1),
                        validators.MatchRegex(
                            r"^[A-Za-z0-9\-_. ]+$",
                            Message(
                                "Valid service names may only contain letters, numbers,"
                                " dashes, underscores, spaces and dots."
                            ),
                        ),
                    ),
                ),
            ),
            "dns": DictElement(
                parameter_form=FixedValue(
                    title=Title("Use DNS resolution to lookup addresses"),
                    value=True,
                ),
            ),
            "type": DictElement(
                parameter_form=SingleChoice(
                    title=Title("Connection type"),
                    elements=(
                        SingleChoiceElement(name="icmp", title=Title("ICMP")),
                        SingleChoiceElement(name="tcp", title=Title("TCP")),
                        SingleChoiceElement(name="udp", title=Title("UDP")),
                    ),
                    prefill=DefaultValue("icmp"),
                ),
            ),
            "count": DictElement(
                parameter_form=Integer(
                    title=Title("Number of send packets per report"),
                    prefill=DefaultValue(10),
                ),
            ),
            "max_hops": DictElement(
                parameter_form=Integer(
                    title=Title("Number of max hops"),
                    prefill=DefaultValue(30),
                ),
            ),
            "enforce_what": DictElement(
                parameter_form=SingleChoice(
                    title=Title("Enforce IPv4 / IPv6"),
                    elements=(
                        SingleChoiceElement(name="ipv4", title=Title("Enforce IPv4")),
                        SingleChoiceElement(name="ipv6", title=Title("Enforce IPv6")),
                    ),
                    prefill=DefaultValue("ipv4"),
                ),
            ),
            "size": DictElement(
                parameter_form=Integer(
                    title=Title("Packet size"),
                    prefill=DefaultValue(64),
                ),
            ),
            "time": DictElement(
                parameter_form=TimeSpan(
                    title=Title("Minimum time between runs"),
                    displayed_magnitudes=(
                        TimeMagnitude.HOUR,
                        TimeMagnitude.MINUTE,
                        TimeMagnitude.SECOND,
                    ),
                ),
            ),
            "port": DictElement(
                parameter_form=Integer(
                    title=Title("UDP/TCP port to connect to"),
                    prefill=DefaultValue(80),
                ),
            ),
            "address": DictElement(
                parameter_form=String(
                    title=Title("Bind to source address"),
                ),
            ),
            "interval": DictElement(
                parameter_form=Integer(
                    title=Title("Time MTR waits between sending pings"),
                    label=Label("Seconds"),
                    prefill=DefaultValue(1),
                ),
            ),
            "timeout": DictElement(
                parameter_form=Integer(
                    title=Title("Ping timeout"),
                    help_text=Help(
                        "The number of seconds to keep the TCP socket open before"
                        " giving up on the connection. This will only affect the"
                        " final hop. Using large values for this, especially"
                        " combined with a short interval, will use up a lot of"
                        " file descriptors on the host running this plug-in."
                    ),
                    label=Label("Seconds"),
                    prefill=DefaultValue(1),
                ),
            ),
        },
    )


def _valuespec_agent_config_mtr() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "Deploy the agent plug-in <tt>mtr</tt> on your target system."
            " Note that <tt>mtr</tt> must be installed on the monitored system."
        ),
        elements={
            "deployment": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    title=Title("Deployment type"),
                    help_text=Help(
                        "This plug-in can only be deployed asynchronously because it"
                        " launches background processes (one per address). Under"
                        " systemd, this only works when being run asynchronously."
                    ),
                    elements=(
                        CascadingSingleChoiceElement(
                            name="cached",
                            title=Title("Deploy the plug-in and run it asynchronously"),
                            parameter_form=TimeSpan(
                                displayed_magnitudes=(
                                    TimeMagnitude.HOUR,
                                    TimeMagnitude.MINUTE,
                                )
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="do_not_deploy",
                            title=Title("Do not deploy the plug-in"),
                            parameter_form=FixedValue(value=None),
                        ),
                    ),
                    prefill=DefaultValue("cached"),
                ),
            ),
            "mtr_config": DictElement(
                required=True,
                parameter_form=List(
                    title=Title("MTR configuration"),
                    add_element_label=Label("Add destination address"),
                    element_template=_address_configuration(),
                ),
            ),
        },
        migrate=migrate,
    )


rule_spec_mtr = AgentConfig(
    title=Title("MTR (Matt's traceroute) (Linux)"),
    name="mtr",
    topic=Topic.NETWORKING,
    parameter_form=_valuespec_agent_config_mtr,
)
