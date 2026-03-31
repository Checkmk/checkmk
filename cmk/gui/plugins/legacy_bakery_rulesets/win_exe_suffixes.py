#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence

from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsWindowsAgent
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import ListOfStrings, Optional, TextInput
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_win_exe_suffixes() -> Optional[Sequence[str]]:
    return Optional(
        valuespec=ListOfStrings(
            default_value=["exe", "bat", "vbs", "ps1"],
            orientation="horizontal",
            valuespec=TextInput(
                size=4,
                regex="^[a-z0-9]{1,8}$",
                regex_error=_("Please specify the extensions in lower case and without dot."),
            ),
        ),
        title=_("Limit script types to execute"),
        help=_(
            "If you want to run your own custom agent plug-ins on Windows, "
            "simply put them into the subdirectory <tt>plugins</tt> "
            "of your agent's installation directory. <i>Local checks</i> work just the "
            "same, but are installed in <tt>local</tt>. Plug-ins that are deployed "
            "with the Agent Bakery are installed by the MSI installer into the same "
            "directory. This ruleset limits the file extensions that the agent "
            "will run. This for example avoids starting a Notepad when a file with "
            "the extension <tt>.txt</tt> is found. <b>Note:</b> If you remove some "
            "of the default extensions, not all of the shipped agent plug-ins will "
            "continue to work!<br><br>Specify the extensions in lower case and without "
            "a leading dot."
        ),
        label=_("Only execute plug-ins with the following extensions:"),
        none_label=_("Execute all files in the plug-ins directory"),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsWindowsAgent,
        name=RuleGroup.AgentConfig("win_exe_suffixes"),
        valuespec=_valuespec_agent_config_win_exe_suffixes,
    )
)
