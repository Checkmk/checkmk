#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.plugins.docker.sections import CONTAINER_SECTIONS, NODE_SECTIONS
from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    MultipleChoice,
    MultipleChoiceElement,
    SingleChoice,
    SingleChoiceElement,
    String,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic


def migrate(value: object) -> Mapping[str, object]:
    if isinstance(value, dict) and "deployment" in value:
        return value
    if value is None:
        return {"deployment": ("do_not_deploy", None)}
    if isinstance(value, dict):
        interval = value.get("interval", 0)
        deployment: tuple[str, float | None] = (
            ("cached", float(interval))
            if isinstance(interval, (int, float)) and interval > 60
            else ("sync", None)
        )
        result: dict[str, object] = {"deployment": deployment}
        for key in (
            "node",
            "containers",
            "container_id",
            "base_url",
            "persist_period_node_disk_usage",
        ):
            if key in value:
                result[key] = value[key]
        return result
    raise ValueError(f"Unexpected value: {value!r}")


def _valuespec_agent_config_mk_docker() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "This will deploy the agent plug-in <tt>mk_docker.py</tt>."
            " You can choose to monitor the node and/or the individual containers."
            " This plug-in requires the Python library 'docker' (at least version 2.0.0) to be"
            " installed on the monitored system, which can be achieved using the command"
            " '<tt>pip install docker</tt>'. Warning: <tt>pip install docker-py</tt>"
            " may install an outdated, incompatible version of the same library."
            " If you want to monitor the containers of multiple Docker nodes"
            " we strongly recommend to set up"
            ' <a href="wato.py?mode=edit_ruleset&varname=piggyback_translation">Piggyback translation rules</a>'
            " to avoid name collisions if containers with the same name exist on"
            " multiple Docker nodes."
        ),
        elements={
            "deployment": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    title=Title("Deployment type"),
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
                                    TimeMagnitude.SECOND,
                                ),
                                prefill=DefaultValue(300.0),
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="do_not_deploy",
                            title=Title("Do not deploy the plug-in"),
                            parameter_form=FixedValue(value=None),
                        ),
                    ),
                    prefill=DefaultValue("sync"),
                ),
            ),
            "node": DictElement(
                parameter_form=MultipleChoice(
                    title=Title("Node sections to skip"),
                    help_text=Help(
                        "Choose which node sections to skip. The respective sections belong to"
                        " the check plug-ins by the name starting with 'docker_node_'."
                        " Note that the disk usage section is notoriously long running."
                        " If you experience performance issues, consider skipping it."
                    ),
                    elements=[
                        MultipleChoiceElement(name=k, title=v) for k, v in NODE_SECTIONS.items()
                    ],
                    prefill=DefaultValue([]),
                ),
            ),
            "containers": DictElement(
                parameter_form=MultipleChoice(
                    title=Title("Container sections to skip"),
                    help_text=Help(
                        "Choose which container sections to skip. The piggybacked host"
                        " name is the container's host name configured below. The"
                        " respective sections belong to the check plug-ins with their names"
                        " starting with 'docker_container_'."
                    ),
                    elements=[
                        MultipleChoiceElement(name=k, title=v)
                        for k, v in CONTAINER_SECTIONS.items()
                    ],
                    prefill=DefaultValue([]),
                ),
            ),
            "container_id": DictElement(
                parameter_form=SingleChoice(
                    title=Title("Host name used for containers"),
                    help_text=Help(
                        "Choose which identifier is used for the monitored containers."
                        " This will affect the name used for the piggyback host"
                        " corresponding to the container, as well as items for"
                        " services created on the node for each container."
                    ),
                    elements=[
                        SingleChoiceElement(
                            name="short",
                            title=Title(
                                "Short - Use the first 12 characters of the Docker container ID"
                            ),
                        ),
                        SingleChoiceElement(
                            name="long",
                            title=Title("Long - Use the full Docker container ID"),
                        ),
                        SingleChoiceElement(
                            name="name",
                            title=Title("Name - Use the name of the container"),
                        ),
                        SingleChoiceElement(
                            name="combined",
                            title=Title("Combine the node name and the name of the container"),
                        ),
                    ],
                    prefill=DefaultValue("short"),
                ),
            ),
            "base_url": DictElement(
                parameter_form=String(
                    title=Title("Base URL for Docker API engine"),
                    help_text=Help(
                        "Provide the base URL for Docker API engine calls. By default"
                        " we are trying to connect via the Unix socket at /var/run/docker.sock."
                    ),
                    prefill=DefaultValue("unix://var/run/docker.sock"),
                ),
            ),
            "persist_period_node_disk_usage": DictElement(
                parameter_form=TimeSpan(
                    title=Title("Persistence period for node disk usage fallback"),
                    help_text=Help("Keep last successful data for"),
                    displayed_magnitudes=(
                        TimeMagnitude.HOUR,
                        TimeMagnitude.MINUTE,
                        TimeMagnitude.SECOND,
                    ),
                    prefill=DefaultValue(90.0),
                ),
            ),
        },
        migrate=migrate,
    )


rule_spec_mk_docker = AgentConfig(
    title=Title("Docker node and containers"),
    name="mk_docker",
    topic=Topic.VIRTUALIZATION,
    parameter_form=_valuespec_agent_config_mk_docker,
)
