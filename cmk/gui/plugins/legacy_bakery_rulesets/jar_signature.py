#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsAgentPlugins
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import Alternative, FixedValue, ListOfStrings, TextInput, Tuple
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_jar_signature() -> Alternative:
    return Alternative(
        title=_("Signatures of certificates in JAR files"),
        help=_(
            "This plug-in can be used to check the remaining life time "
            "of SSL certificates that are contained in JAVA JAR files. "
            "The tool <tt>jarsigner -verify</tt> is being called for "
            "that purpose."
        ),
        elements=[
            Tuple(
                title=_("Deploy plug-in for JAR signatures"),
                elements=[
                    TextInput(
                        title=_("<tt>JAVA_HOME</tt> - path to Java installation"),
                        size=80,
                        allow_empty=False,
                    ),
                    ListOfStrings(
                        title=_("Path-patterns where to search for Jar files"),
                        help=_("You can use <tt>*</tt> and <tt>?</tt> here."),
                        valuespec=TextInput(
                            size=80,
                            regex="^/[^ \t]+$",
                            regex_error=_(
                                "File patterns must begin with <tt>/</tt> "
                                "and must not contain spaces."
                            ),
                            allow_empty=False,
                        ),
                        allow_empty=False,
                    ),
                ],
            ),
            FixedValue(
                value=None,
                title=_("Do not deploy plug-in for JAR signatures"),
                totext=_("(disabled)"),
            ),
        ],
        default_value=(
            "/home/oracle/bin/jdk_latest_version",
            ["/home/oracle/fmw/11gR2/as_1/forms/java/*.jar"],
        ),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsAgentPlugins,
        name=RuleGroup.AgentConfig("jar_signature"),
        valuespec=_valuespec_agent_config_jar_signature,
    )
)
