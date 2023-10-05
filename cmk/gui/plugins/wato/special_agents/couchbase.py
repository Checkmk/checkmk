#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.utils.rulesets.definition import RuleGroup

from cmk.gui.i18n import _
from cmk.gui.valuespec import Dictionary, Integer, ListOfStrings, NetworkPort, TextInput, Tuple
from cmk.gui.wato import IndividualOrStoredPassword, RulespecGroupDatasourceProgramsApps
from cmk.gui.watolib.rulespecs import HostRulespec, Rulespec, rulespec_registry


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
                NetworkPort(
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
                        IndividualOrStoredPassword(
                            title=_("Password of the user"), allow_empty=False
                        ),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=Rulespec.FACTORY_DEFAULT_UNUSED,
        group=RulespecGroupDatasourceProgramsApps,
        name=RuleGroup.SpecialAgents("couchbase"),
        valuespec=_valuespec_special_agents_couchbase,
    )
)
