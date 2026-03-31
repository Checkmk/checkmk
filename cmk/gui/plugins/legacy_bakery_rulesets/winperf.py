#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsAgentPlugins
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import ListOf, TextInput, Tuple
from cmk.utils.rulesets.definition import RuleGroup


def _valuespec_agent_config_winperf() -> ListOf[tuple[str, str]]:
    return ListOf(
        valuespec=Tuple(
            elements=[
                TextInput(
                    title=_("Section name"),
                    help=_(
                        "Choose a name here. If you choose <tt>foo</tt> then section header and thus the "
                        "name of the required check plug-in will be &lt;&lt;&lt;winperf_foo&gt;&gt;&gt;."
                    ),
                    regex="^[a-z]+[a-z0-9_]*$",
                    regex_error=_("Use only lower case letters, digits, and underscores here."),
                    size=20,
                ),
                TextInput(
                    title=_("Counter-object name or number"),
                    size=40,
                    allow_empty=False,
                    forbidden_chars="\\",
                ),
            ]
        ),
        add_label=_("Add Counter Object"),
        title=_("Windows Performance-Counter objects"),
        help=_(
            "Here you can configure which performance counter objects the Windows agent "
            "should extract and provide to the Checkmk server. You can either specify "
            "counter numbers or names. Note: numbers might be host-specific. Names are "
            "language-specific. Also note that you need to specify names of counter <i>objects</i>, "
            "not of single counters. In order to make use of the counters you need a "
            "matching check plug-in on the Checkmk server."
        ),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsAgentPlugins,
        name=RuleGroup.AgentConfig("winperf"),
        valuespec=_valuespec_agent_config_winperf,
    )
)
