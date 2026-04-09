#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.rulesets.v1 import Help, Label, Title
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
    if isinstance(value, dict):
        return value  # already in new format
    if value is None:
        return {"deployment": ("do_not_deploy", None)}
    if not isinstance(value, (tuple, list)):
        raise ValueError(f"Unexpected value in nginx_status migration: {value!r}")
    mode, data = value
    if mode is None:
        return {"deployment": ("do_not_deploy", None)}
    return {"deployment": ("sync", None), "instances": (mode, data)}


def _valuespec_agent_config_nginx_status() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "If you activate this option, then the agent plug-in <tt>nginx_status</tt> will be deployed. "
            "For each configured or detected NGINX instance there will be one new service with detailed "
            "statistics of the current number of clients and processes and their various states."
        ),
        elements={
            "deployment": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    title=Title("Deployment type"),
                    prefill=DefaultValue("sync"),
                    elements=(
                        CascadingSingleChoiceElement(
                            name="sync",
                            title=Title("Deploy the plug-in and run it synchronously"),
                            parameter_form=FixedValue(value=None),
                        ),
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
                ),
            ),
            "instances": DictElement(
                parameter_form=CascadingSingleChoice(
                    title=Title("NGINX web servers (Linux)"),
                    prefill=DefaultValue("autodetect"),
                    elements=(
                        CascadingSingleChoiceElement(
                            name="autodetect",
                            title=Title(
                                "Autodetect instances, expect HTTPS on the following ports:"
                            ),
                            parameter_form=List(
                                element_template=Integer(
                                    title=Title("HTTPS port"),
                                    prefill=DefaultValue(443),
                                    custom_validate=(validators.NetworkPort(),),
                                ),
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="static",
                            title=Title("Specific list of instances"),
                            parameter_form=List(
                                element_template=Dictionary(
                                    elements={
                                        "protocol": DictElement(
                                            required=True,
                                            parameter_form=SingleChoice(
                                                title=Title("Protocol"),
                                                elements=[
                                                    SingleChoiceElement(
                                                        name="http", title=Title("HTTP")
                                                    ),
                                                    SingleChoiceElement(
                                                        name="https", title=Title("HTTPS")
                                                    ),
                                                ],
                                                prefill=DefaultValue("http"),
                                            ),
                                        ),
                                        "address": DictElement(
                                            required=True,
                                            parameter_form=String(
                                                title=Title("IP address (IPv4 or IPv6)"),
                                                prefill=DefaultValue("127.0.0.1"),
                                            ),
                                        ),
                                        "port": DictElement(
                                            required=True,
                                            parameter_form=Integer(
                                                title=Title("TCP port number"),
                                                prefill=DefaultValue(80),
                                                custom_validate=(validators.NetworkPort(),),
                                            ),
                                        ),
                                        "page": DictElement(
                                            parameter_form=String(
                                                title=Title("URI (page name)"),
                                                prefill=DefaultValue("nginx_status"),
                                            ),
                                        ),
                                    },
                                ),
                                add_element_label=Label("Add NGINX instance"),
                            ),
                        ),
                    ),
                ),
            ),
        },
        migrate=migrate,
    )


rule_spec_nginx_status = AgentConfig(
    title=Title("NGINX web servers (Linux)"),
    name="nginx_status",
    topic=Topic.APPLICATIONS,
    parameter_form=_valuespec_agent_config_nginx_status,
)
