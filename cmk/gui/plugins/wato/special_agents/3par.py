#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.rulesets.definition import RuleGroup

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common import RulespecGroupDatasourceProgramsHardware
from cmk.gui.plugins.wato.utils import (
    HostRulespec,
    MigrateToIndividualOrStoredPassword,
    rulespec_registry,
)
from cmk.gui.valuespec import Dictionary, DropdownChoice, ListOfStrings, NetworkPort, TextInput


def _valuespec_special_agents_3par() -> Dictionary:
    return Dictionary(
        title=_("3PAR Configuration"),
        elements=[
            (
                "user",
                TextInput(
                    title=_("Username"),
                    allow_empty=False,
                ),
            ),
            (
                "password",
                MigrateToIndividualOrStoredPassword(
                    title=_("Password"),
                    allow_empty=False,
                ),
            ),
            (
                "port",
                NetworkPort(
                    title=_("TCP port number"),
                    help=_("Port number that 3par is listening on. The default is 8080."),
                    default_value=8080,
                    minvalue=1,
                    maxvalue=65535,
                ),
            ),
            (
                "verify_cert",
                DropdownChoice(
                    title=_("SSL certificate verification"),
                    choices=[
                        (True, _("Activate")),
                        (False, _("Deactivate")),
                    ],
                ),
            ),
            (
                "values",
                ListOfStrings(
                    title=_("Values to fetch"),
                    orientation="horizontal",
                    help=_(
                        "Possible values are the following: cpgs, volumes, hosts, capacity, "
                        "system, ports, remotecopy, hostsets, volumesets, vluns, flashcache, "
                        "users, roles, qos.\n"
                        "If you do not specify any value the first seven are used as default."
                    ),
                ),
            ),
        ],
        optional_keys=["values"],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourceProgramsHardware,
        name=RuleGroup.SpecialAgents("3par"),
        title=lambda: _("3PAR Configuration"),
        valuespec=_valuespec_special_agents_3par,
    )
)
