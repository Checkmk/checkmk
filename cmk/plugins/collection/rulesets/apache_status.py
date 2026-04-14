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


def _convert_old_instance(inst: object) -> Mapping[str, object]:
    if not isinstance(inst, (tuple, list)) or len(inst) < 2:
        raise ValueError(f"Unexpected instance format: {inst!r}")
    (protocol, cafile), address, port, name = inst

    result: dict[str, object] = {"protocol": protocol, "address": address}
    if port is not None:
        result["port"] = port
    if name:
        result["instance"] = name
    if cafile is not None:
        result["cafile"] = cafile
    return result


def migrate(value: object) -> Mapping[str, object]:
    if isinstance(value, dict) and "deployment" in value:
        return value
    if value is None:
        return {"deployment": ("do_not_deploy", None)}
    if not isinstance(value, (tuple, list)):
        raise ValueError(f"Unexpected value in apache_status migration: {value!r}")
    mode, data = value[0], value[1]
    if mode is None:
        return {"deployment": ("do_not_deploy", None)}
    if mode == "autodetect":
        return {"deployment": ("sync", None), "instances": ("autodetect", data)}
    if mode == "static":
        instances = [_convert_old_instance(inst) for inst in data]
        return {"deployment": ("sync", None), "instances": ("static", instances)}
    raise ValueError(f"Unexpected mode in apache_status migration: {mode!r}")


def _valuespec_agent_config_apache_status() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "If you activate this option, then the agent plug-in <tt>apache_status</tt> will be "
            "deployed. For each configured or detected Apache instance there will be one new "
            "service with detailed statistics of the current number of clients and processes "
            "and their various states."
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
                                ),
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
                    title=Title("Apache web servers (Linux)"),
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
                                        "cafile": DictElement(
                                            parameter_form=String(
                                                title=Title("CA certificate"),
                                                help_text=Help(
                                                    "An absolute path to a CA certificate "
                                                    "(only relevant for HTTPS)"
                                                ),
                                                prefill=DefaultValue("/etc/ssl/certs/cert.pem"),
                                            ),
                                        ),
                                        "address": DictElement(
                                            required=True,
                                            parameter_form=String(
                                                title=Title("IPv4 address"),
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
                                        "instance": DictElement(
                                            parameter_form=String(
                                                title=Title(
                                                    "Name of the instance in the monitoring"
                                                ),
                                                help_text=Help(
                                                    "If you do not specify a name here, then "
                                                    "the TCP port number will be used as an "
                                                    "instance name."
                                                ),
                                            ),
                                        ),
                                    },
                                ),
                                add_element_label=Label("Add Apache instance"),
                            ),
                        ),
                    ),
                ),
            ),
        },
        migrate=migrate,
    )


rule_spec_apache_status = AgentConfig(
    title=Title("Apache web servers (Linux)"),
    name="apache_status",
    topic=Topic.APPLICATIONS,
    parameter_form=_valuespec_agent_config_apache_status,
)
