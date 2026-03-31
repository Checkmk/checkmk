#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsAgentPlugins
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import ListOfStrings, TextInput
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_fileinfo() -> ListOfStrings:
    return ListOfStrings(
        title=_("Count, size and age of files"),
        size=80,
        help=_(
            "<p>Here you can specify a list of filename patterns to be sent by the "
            "agent in the section <tt>fileinfo</tt>. Use globbing patterns like "
            "<tt>C:\\foo\\*.log</tt> or <tt>/var/*/*.log</tt> here. Per default each found file "
            "will be monitored for size and age. By building groups you can alternatively "
            "monitor a collection of files as an entity and monitor the count, total size, the largest, "
            "smallest oldest or newest file. Note: if you specify more than one matching rule, then "
            "<b>all</b> matching rules will be used for defining pattern - not just the "
            " first one.</p>"
            "<p>On Linux the variable $DATE:format-spec$ can be used for the current "
            "time/date, where format-spec is a list of time format directives of the unix "
            " date command. Example: $DATE:%Y%m%d$ is todays date, in the format YYYYMMDD. "
            "Using this option the agent will only send files containing the current date. "
            "Date variables can be used together with the rules File Grouping Patterns and "
            "Size, age and count of file groups to monitor if files are created in a directory "
            "on a daily basis. Note that the Option Only check during the following times of the day "
            "should be set. Otherwise a warning may be displayed if the file for the current day is "
            "not present yet.</p>"
        ),
        valuespec=TextInput(size=80),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsAgentPlugins,
        match_type="list",
        name=RuleGroup.AgentConfig("fileinfo"),
        valuespec=_valuespec_agent_config_fileinfo,
    )
)
