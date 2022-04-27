#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common import RulespecGroupDatasourceProgramsApps
from cmk.gui.plugins.wato.utils import HostRulespec, PasswordFromStore, rulespec_registry
from cmk.gui.valuespec import Dictionary, Integer, ListOfStrings, TextInput, Tuple
from cmk.gui.watolib.rulespecs import Rulespec


def _valuespec_special_agents_couchbase():
    return Dictionary(
        title=_("Couchbase servers"),
        help=_(
            "This rule allows to select a Couchbase server to monitor as well as "
            "configure buckets for further checks"
        ),
        elements=[
            (
                "buckets",
                ListOfStrings(title=_("Bucket names"), help=_("Name of the Buckets to monitor.")),
            ),
            (
                "timeout",
                Integer(
                    title=_("Timeout"), default_value=10, help=_("Timeout for requests in seconds.")
                ),
            ),
            (
                "port",
                Integer(
                    title=_("Port"),
                    default_value=8091,
                    help=_("The port that is used for the api call."),
                ),
            ),
            (
                "authentication",
                Tuple(
                    title=_("Authentication"),
                    help=_("The credentials for api calls with authentication."),
                    elements=[
                        TextInput(title=_("Username"), allow_empty=False),
                        PasswordFromStore(title=_("Password of the user"), allow_empty=False),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=Rulespec.FACTORY_DEFAULT_UNUSED,
        group=RulespecGroupDatasourceProgramsApps,
        name="special_agents:couchbase",
        valuespec=_valuespec_special_agents_couchbase,
    )
)
