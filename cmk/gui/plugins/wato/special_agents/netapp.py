#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common import RulespecGroupDatasourceProgramsHardware
from cmk.gui.plugins.wato.utils import HostRulespec, IndividualOrStoredPassword, rulespec_registry
from cmk.gui.valuespec import Dictionary, ListChoice, TextInput, Transform


def _valuespec_special_agents_netapp():
    return Transform(
        valuespec=Dictionary(
            elements=[
                (
                    "username",
                    TextInput(
                        title=_("Username"),
                        allow_empty=False,
                    ),
                ),
                (
                    "password",
                    IndividualOrStoredPassword(
                        title=_("Password"),
                        allow_empty=False,
                    ),
                ),
                (
                    "skip_elements",
                    ListChoice(
                        choices=[
                            ("ctr_volumes", _("Do not query volume performance counters")),
                        ],
                        title=_("Performance improvements"),
                        help=_(
                            "Here you can configure whether the performance counters should get queried. "
                            "This can save quite a lot of CPU load on larger systems."
                        ),
                    ),
                ),
            ],
            title=_("NetApp via WebAPI"),
            help=_(
                "This rule set selects the NetApp special agent instead of the normal Check_MK Agent "
                "and allows monitoring via the NetApp Web API. To access the data the "
                "user requires permissions to several API classes. They are shown when you call the agent with "
                "<tt>agent_netapp --help</tt>. The agent itself is located in the site directory under "
                "<tt>~/share/check_mk/agents/special</tt>."
            ),
            optional_keys=False,
        ),
        forth=lambda x: dict([("skip_elements", [])] + list(x.items())),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourceProgramsHardware,
        name="special_agents:netapp",
        valuespec=_valuespec_special_agents_netapp,
    )
)
