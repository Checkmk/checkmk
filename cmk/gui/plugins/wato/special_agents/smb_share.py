#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common import RulespecGroupDatasourceProgramsApps
from cmk.gui.plugins.wato.utils import HostRulespec, IndividualOrStoredPassword, rulespec_registry
from cmk.gui.valuespec import Dictionary, HostAddress, ListOfStrings, TextInput, Tuple


def _valuespec_special_agents_smb_share():
    return Dictionary(
        elements=[
            (
                "hostname",
                TextInput(
                    title="Hostname",
                    allow_empty=False,
                    help=_(
                        "<p>Usually Checkmk will use the hostname of the host it is attached to. "
                        "With this option you can override this parameter.</p>"
                    ),
                ),
            ),
            (
                "ip_address",
                HostAddress(
                    title=_("IP address"),
                    allow_empty=False,
                    allow_ipv6_address=False,
                    help=_(
                        "<p>Usually Checkmk will use the primary IP address of the host it is "
                        "attached to. With this option you can override this parameter.</p>"
                    ),
                ),
            ),
            (
                "authentication",
                Tuple(
                    title=_("Authentication"),
                    elements=[
                        TextInput(title=_("Username"), allow_empty=False),
                        IndividualOrStoredPassword(title=_("Password"), allow_empty=False),
                    ],
                ),
            ),
            (
                "patterns",
                ListOfStrings(
                    title=_("File patterns"),
                    size=80,
                    help=_(
                        "<p>Here you can specify a list of filename patterns to be sent by the "
                        "agent in the section <tt>fileinfo</tt>. UNC paths with globbing patterns "
                        "are used here, e.g. <tt>\\\\hostname\\share name\\*\\foo\\*.log</tt>. "
                        "Wildcards are not allowed in host or share names. "
                        "Per default each found file will be monitored for size and age. "
                        "By building groups you can alternatively monitor a collection "
                        "of files as an entity and monitor the count, total size, the largest, "
                        "smallest oldest or newest file. Note: if you specify more than one matching rule, then "
                        "<b>all</b> matching rules will be used for defining pattern - not just the "
                        " first one.</p>"
                    ),
                    valuespec=TextInput(size=80),
                ),
            ),
        ],
        optional_keys=["hostname", "ip_address", "authentication"],
        title=_("SMB Share fileinfo"),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourceProgramsApps,
        name="special_agents:smb_share",
        valuespec=_valuespec_special_agents_smb_share,
    )
)
