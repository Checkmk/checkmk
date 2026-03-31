#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsAgentPlugins
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import (
    Age,
    Alternative,
    Dictionary,
    DropdownChoice,
    FixedValue,
    ListChoice,
    TextInput,
    Transform,
)
from cmk.utils.rulesets.definition import RuleGroup


def _agent_config_mk_docker_invert_choices_node(selected: list[str]) -> list[str]:
    return [key for key, _label in _agent_config_mk_docker_choices_node() if key not in selected]


def _agent_config_mk_docker_choices_cont() -> list[tuple[str, str]]:
    return [
        ("docker_container_node_name", _("Node name: Inventorize the nodes' name")),
        (
            "docker_container_status",
            "Status: %s" % _("Create status and (if configured) health services"),
        ),
        ("docker_container_labels", "Labels: %s" % _("Inventorize the labels")),
        (
            "docker_container_network",
            "Network: %s" % _("Inventorize network configuration information"),
        ),
        (
            "docker_container_agent",
            _("Checkmk agent: Execute the Checkmk agent within running containers"),
        ),
        ("docker_container_mem", _("Check containers memory usage")),
        ("docker_container_cpu", _("Check containers CPU utilization")),
        ("docker_container_diskstat", _("Check containers disk status")),
    ]


def _agent_config_mk_docker_choices_node() -> list[tuple[str, str]]:
    return [
        (
            "docker_node_info",
            "Info: %s" % _("Daemon state and summarized count of containers and their states"),
        ),
        (
            "docker_node_disk_usage",
            "Disk usage: %s" % _("Information similar to 'docker system df' output"),
        ),
        (
            "docker_node_images",
            "Images: %s"
            % _(
                "Inventorize image information such as creation time, size,"
                " labels and the amount of containers running them."
            ),
        ),
        (
            "docker_node_network",
            "Network: %s" % _("Inventorize containers' network configuration"),
        ),
    ]


def _agent_config_mk_docker_invert_choices_cont(selected: list[str]) -> list[str]:
    return [key for key, _label in _agent_config_mk_docker_choices_cont() if key not in selected]


def _valuespec_agent_config_mk_docker() -> Alternative:
    return Alternative(
        title=_("Docker node and containers"),
        help=_(
            "This will deploy the agent plug-in <tt>mk_docker.py</tt>."
            " You can choose to monitor the node and/or the individual containers."
            " This plug-in requires the python library 'docker' (at least version 2.0.0) to be"
            " installed on the monitored system, which can be achieved using the command"
            " '<tt>pip install docker</tt>'. WARNING: <tt>pip install docker-py</tt>"
            " may install an outdated, incompatible version of the same library."
            " If you want to monitor the containers of multiple docker nodes"
            " we strongly recommend to set up"
            ' <a href="wato.py?mode=edit_ruleset&varname=piggyback_translation">Piggyback translation rules</a>'
            " to avoid name collisions if containers with the same name exist on"
            " multiple docker nodes."
        ),
        elements=[
            Dictionary(
                title=_("Deploy the Docker plug-in"),
                elements=[
                    (
                        "node",
                        Transform(
                            valuespec=ListChoice(
                                title=_("Gathered node information"),
                                help=_(
                                    "Choose how to monitor the Docker node. You can uncheck"
                                    " individual sections, if you do not need the corresponding"
                                    " services. The respective checkboxes belong to the check"
                                    " plug-ins by the name starting with 'docker_node_' (e.g., the"
                                    " 'Disk usage:' checkbox belongs to 'docker_node_disk_usage')."
                                    " Note that the disk usage section is notoriously long running."
                                    " If you experience performance issues, consider disabling it."
                                ),
                                choices=_agent_config_mk_docker_choices_node(),
                                toggle_all=True,
                                default_value=[
                                    key for key, _label in _agent_config_mk_docker_choices_node()
                                ],
                            ),
                            from_valuespec=_agent_config_mk_docker_invert_choices_node,
                            to_valuespec=_agent_config_mk_docker_invert_choices_node,
                        ),
                    ),
                    (
                        "containers",
                        Transform(
                            valuespec=ListChoice(
                                title=_("Gathered container information (piggybacked)"),
                                help=_(
                                    "In order to monitor Docker containers the plug-in"
                                    " <tt>mk_docker.py</tt> collects the following information of"
                                    " each Docker container as piggyback data. The piggybacked host"
                                    " name is the container's host name configured below. The"
                                    " respective checkboxes belong to the check plug-ins with their names"
                                    " starting with 'docker_container_' (e.g. the 'Node name:'"
                                    " checkbox belongs to 'docker_container_node_name')."
                                ),
                                choices=_agent_config_mk_docker_choices_cont(),
                                toggle_all=True,
                                default_value=[
                                    key for key, _label in _agent_config_mk_docker_choices_cont()
                                ],
                            ),
                            from_valuespec=_agent_config_mk_docker_invert_choices_cont,
                            to_valuespec=_agent_config_mk_docker_invert_choices_cont,
                        ),
                    ),
                    (
                        "container_id",
                        DropdownChoice(
                            title=_("Host name used for containers"),
                            help=_(
                                "Choose which identifier is used for the monitored containers."
                                " This will affect the name used for the piggyback host"
                                " corresponding to the container, as well as items for"
                                " services created on the node for each container."
                            ),
                            choices=[
                                (
                                    "short",
                                    _(
                                        "Short - Use the first 12 characters of the Docker container ID"
                                    ),
                                ),
                                ("long", _("Long - Use the full Docker container ID")),
                                ("name", _("Name - Use the name of the container")),
                                (
                                    "combined",
                                    _("Combine the node name and the name of the container"),
                                ),
                            ],
                        ),
                    ),
                    (
                        "base_url",
                        TextInput(
                            title=_("Base URL for Docker API engine"),
                            help=_(
                                "Provide the base URL for Docker API engine calls. By default"
                                " we are trying to connect via the Unix socket at %s."
                            )
                            % "/var/run/docker.sock",
                            default_value="unix://var/run/docker.sock",
                        ),
                    ),
                    (
                        "persist_period_node_disk_usage",
                        Age(
                            title=_("Persistence period for node disk usage fallback"),
                            label=_("Keep last successful data for"),
                            display=["hours", "minutes", "seconds"],
                            default_value=90,
                        ),
                    ),
                    (
                        "interval",
                        Age(
                            title=_("Run asynchronously"),
                            label=_("Interval for collecting data"),
                            default_value=300,
                        ),
                    ),
                ],
                optional_keys=["interval", "base_url", "persist_period_node_disk_usage"],
            ),
            FixedValue(
                value=None,
                title=_("Do not deploy the Docker plug-in"),
                totext=_("(disabled)"),
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsAgentPlugins,
        name=RuleGroup.AgentConfig("mk_docker"),
        valuespec=_valuespec_agent_config_mk_docker,
    )
)
