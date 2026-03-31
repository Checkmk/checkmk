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
from cmk.gui.valuespec import Alternative, Dictionary, FixedValue, TextInput
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_python_plugins() -> Dictionary:
    return Dictionary(
        title=_("Python agent plug-in execution (Linux, Unix)"),
        help=_(
            "By default, Python agent plug-ins are written in Python 3. However,"
            " since Python 2 is still often seen on many machines, we provide a"
            " fallback Python 2 version alongside the Python 3 version of the"
            " plug-ins, that is used as a fallback if there is no Python 3 version"
            " available on the host.<br>"
            "With this rule, you can enforce the usage of either the Python 2 or"
            " Python 3 version.<br>"
            "Additionally, you can provide a command, that will be used for Python"
            " plug-in execution."
        ),
        elements=[
            (
                "version",
                Alternative(
                    title=_("Python version for execution of Python agent plug-ins"),
                    help=_(
                        "The Checkmk agent Unix will detect a Python 3 installation by looking for the command <tt>python3</tt>, and a Python 2 installation by looking for the commands <tt>python2</tt> or <tt>python</tt>. If this doesn't match to your host's Python installation, e.g., if Python 3 is available via <tt>python</tt>, you can enforce the right version by setting this rule entry."
                    ),
                    elements=[
                        FixedValue(
                            value="auto",
                            title="Auto",
                            totext=_("Automatic detection (Python 3 > Python 2)"),
                        ),
                        FixedValue(
                            value="python2", title="Python 2", totext=_("Enforce Python 2 version")
                        ),
                        FixedValue(
                            value="python3", title="Python 3", totext=_("Enforce Python 3 version")
                        ),
                    ],
                ),
            ),
            (
                "command",
                TextInput(
                    title=_("Provide command for python script execution"),
                    help=_(
                        "By default, the Checkmk Unix agent will execute Python 3 plug-ins with <tt>python3</tt> and Python 2 plug-ins with <tt>python2</tt> or <tt>python</tt> (depending on the command found on the host system). Here you can specify a specific command, independent of the script that will be executed."
                    ),
                    allow_empty=False,
                ),
            ),
        ],
        optional_keys=["command"],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsLinuxUnixAgent,
        match_type="dict",
        name=RuleGroup.AgentConfig("python_plugins"),
        valuespec=_valuespec_agent_config_python_plugins,
    )
)
