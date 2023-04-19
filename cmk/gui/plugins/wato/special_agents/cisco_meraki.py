#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common import RulespecGroupDatasourceProgramsApps
from cmk.gui.plugins.wato.utils import (
    HostRulespec,
    HTTPProxyReference,
    IndividualOrStoredPassword,
    rulespec_registry,
)
from cmk.gui.valuespec import Dictionary, DualListChoice, ListOfStrings, ValueSpec


def _valuespec_special_agent_cisco_meraki() -> ValueSpec:
    return Dictionary(
        title=_("Cisco Meraki"),
        elements=[
            ("api_key", IndividualOrStoredPassword(title=_("API Key"), allow_empty=False)),
            (
                "proxy",
                HTTPProxyReference(),
            ),
            (
                "sections",
                DualListChoice(
                    title=_("Sections"),
                    choices=[
                        ("licenses-overview", _("Organisation licenses overview")),
                        ("device-statuses", _("Organisation device statuses")),
                        ("sensor-readings", _("Organisation sensor readings")),
                    ],
                    rows=12,
                ),
            ),
            (
                "orgs",
                ListOfStrings(title=_("Organisations")),
            ),
        ],
        optional_keys=["proxy", "sections", "orgs"],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourceProgramsApps,
        name="special_agents:cisco_meraki",
        valuespec=_valuespec_special_agent_cisco_meraki,
    )
)
