#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common import RulespecGroupDatasourceProgramsHardware
from cmk.gui.plugins.wato.utils import HostRulespec, IndividualOrStoredPassword, rulespec_registry
from cmk.gui.valuespec import (
    Dictionary,
    DropdownChoice,
    Integer,
    ListOfStrings,
    TextInput,
    Transform,
)


def _special_agents_3par_transform(v):
    v.setdefault("verify_cert", False)
    v.setdefault("port", 8080)
    return v


def _valuespec_special_agents_3par():
    return Transform(
        valuespec=Dictionary(
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
                    IndividualOrStoredPassword(
                        title=_("Password"),
                        allow_empty=False,
                    ),
                ),
                (
                    "port",
                    Integer(
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
        ),
        forth=_special_agents_3par_transform,
    )


# verify_cert was added with 1.5.0p1

rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourceProgramsHardware,
        name="special_agents:3par",
        title=lambda: _("3PAR Configuration"),
        valuespec=_valuespec_special_agents_3par,
    )
)
