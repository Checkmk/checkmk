#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsLinuxUnixAgent
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    HostRulespec,
    rulespec_registry,
)
from cmk.gui.valuespec import AbsoluteDirname, Dictionary
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_agent_paths() -> Dictionary:
    return Dictionary(
        title=_("Installation paths for agent files (Linux, Unix) (deprecated)"),
        help=_(
            "The agent installation path configuration now simplifies to one single directory,"
            " which can be configured with the new <i>Customize agent package</i> rule set."
            "<br>When configuring <i>Customize agent package</i>, matching rules from"
            " this rule set will be ignored."
            "<br><b>Note</b>: When updating agents to the new directory structure, please keep"
            " this rule set until the agent update is done. The agent package will read the"
            " old installation paths to migrate your files to the new directory structure."
        ),
        elements=[
            (
                "bin",
                AbsoluteDirname(
                    title=_("Directory for binaries (executables)"),
                    default_value="/usr/bin",
                    help=_(
                        "In this directory will be installed <tt>check_mk_agent</tt>,"
                        " <tt>waitmax</tt> and possibly other binaries that are needed"
                        " by the agent."
                    ),
                    allow_empty=False,
                ),
            ),
            (
                "config",
                AbsoluteDirname(
                    title=_("Directory for configuration files"),
                    default_value="/etc/check_mk",
                    allow_empty=False,
                ),
            ),
            (
                "lib",
                AbsoluteDirname(
                    title=_("Base directory for <tt>plug-ins</tt> and <tt>local</tt>"),
                    default_value="/usr/lib/check_mk_agent",
                    allow_empty=False,
                ),
            ),
            (
                "var",
                AbsoluteDirname(
                    title=_("Base directory for variable data (caches, state files)"),
                    default_value="/var/lib/check_mk_agent",
                    help=_(
                        "If you change this paths away from its default then the package "
                        "will <b>not</b> delete the contents of that directory when uninstalling."
                    ),
                    allow_empty=False,
                ),
            ),
            (
                "tmp",
                AbsoluteDirname(
                    title=_(
                        "Directory for storage of temporary data (set TMPDIR environment variable)"
                    ),
                    help=_(
                        "Some agent commands or plug-ins may follow the environment variable"
                        " TMPDIR for storage of temporary files."
                        " For some reasons, you might want to adapt this path."
                        ' Namely, the agent updater won\'t work with a "/tmp" dir that'
                        ' is mounted with a "noexec"-flag. Please note that the'
                        " Checkmk Agent does no automatic cleaning on this custom path."
                    ),
                    allow_empty=False,
                ),
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsLinuxUnixAgent,
        match_type="dict",
        name=RuleGroup.AgentConfig("agent_paths"),
        valuespec=_valuespec_agent_config_agent_paths,
        deprecation_planned=True,
    )
)
