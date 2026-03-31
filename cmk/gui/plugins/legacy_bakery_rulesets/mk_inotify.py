#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsAgentPlugins
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import (
    Alternative,
    FixedValue,
    Integer,
    ListChoice,
    ListOf,
    ListOfStrings,
    TextInput,
    Tuple,
)
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_mk_inotify() -> Alternative:
    return Alternative(
        title=_("Monitor file operations with Inotify (Linux)"),
        help=_(
            "The Inotify (Inode notify) is a Linux kernel subsystem that acts to extend "
            "file systems to notice changes to the file system. The Inotify plug-in collects these "
            "changes and reports them back to the monitoring system. You also need to install the "
            "pyinotify Python plug-in onto the target system."
        ),
        elements=[
            FixedValue(value=None, title=_("Do not deploy Inotify plug-in"), totext=""),
            Tuple(
                title=_("Deploy Inotify plug-in"),
                elements=[
                    Integer(
                        title=_("Plug-in heartbeat timeout"),
                        default_value=120,
                        unit=_("seconds"),
                        help=_(
                            "The Inotify is running permanently on the target system "
                            "and expects regular heartbeats to "
                            "continue running. If no heartbeat is received over this "
                            "time period, the plug-in simply stops. It starts again, the "
                            "next time the check_mk_agent is triggered."
                        ),
                    ),
                    Integer(
                        title="Save interval",
                        default_value=10,
                        unit=_("seconds"),
                        help=_("The time interval statistical data is saved to disk"),
                    ),
                    Integer(
                        title=_("Maximum messages per save interval"),
                        default_value=100,
                        unit=_("messages"),
                        help=_("The maximum number of messages per time interval"),
                    ),
                    Integer(
                        title=_("Statistic file retention time"),
                        default_value=120,
                        unit=_("seconds"),
                        help=_(
                            "How long statistics files are kept on the target system. "
                            "This time should be at least double the check interval."
                        ),
                    ),
                    ListOf(
                        valuespec=Alternative(
                            elements=[
                                Tuple(
                                    title=_("Monitor all files in folder"),
                                    elements=[
                                        TextInput(title=_("Folder path"), size=60),
                                        ListChoice(
                                            title=_("Operation"),
                                            choices=[
                                                ("create", _("File created")),
                                                ("delete", _("File deleted")),
                                                ("open", _("File opened")),
                                                ("modify", _("File modified")),
                                                ("access", _("File accessed")),
                                                ("movedfrom", _("File moved from")),
                                                ("movedto", _("File moved to")),
                                                ("moveself", _("File move self")),
                                            ],
                                        ),
                                    ],
                                ),
                                Tuple(
                                    title=_("Monitor specific files in folder"),
                                    elements=[
                                        TextInput(title=_("Folder path"), size=60),
                                        ListOfStrings(
                                            title=_("File name"), size=20, orientation="horizontal"
                                        ),
                                        ListChoice(
                                            title=_("Operation"),
                                            choices=[
                                                ("create", _("File created")),
                                                ("delete", _("File deleted")),
                                                ("open", _("File opened")),
                                                ("modify", _("File modified")),
                                                ("access", _("File accessed")),
                                                ("movedfrom", _("File moved from")),
                                                ("movedto", _("File moved to")),
                                                ("moveself", _("File move self")),
                                            ],
                                        ),
                                    ],
                                ),
                            ]
                        ),
                        add_label=_("Add files to be monitored"),
                    ),
                ],
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsAgentPlugins,
        name=RuleGroup.AgentConfig("mk_inotify"),
        valuespec=_valuespec_agent_config_mk_inotify,
    )
)
