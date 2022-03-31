#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import cmk.gui.watolib as watolib
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common import RulespecGroupDatasourceProgramsApps
from cmk.gui.plugins.wato.utils import HostRulespec, PasswordFromStore, rulespec_registry
from cmk.gui.valuespec import (
    Dictionary,
    DropdownChoice,
    Integer,
    ListChoice,
    ListOfStrings,
    TextInput,
)


def _factory_default_special_agents_elasticsearch():
    # No default, do not use setting if no rule matches
    return watolib.Rulespec.FACTORY_DEFAULT_UNUSED


def _valuespec_special_agents_elasticsearch():
    return Dictionary(
        optional_keys=["user", "password"],
        title=_("Elasticsearch"),
        help=_("Requests data about Elasticsearch clusters, nodes and indices."),
        elements=[
            (
                "hosts",
                ListOfStrings(
                    title=_("Hostnames to query"),
                    help=_(
                        "Use this option to set which host should be checked by the special agent. If the "
                        "connection to the first server fails, the next server will be queried (fallback). "
                        "The check will only output data from the first host that sends a response."
                    ),
                    size=32,
                    allow_empty=False,
                ),
            ),
            ("user", TextInput(title=_("Username"), size=32, allow_empty=True)),
            (
                "password",
                PasswordFromStore(
                    title=_("Password of the user"),
                    allow_empty=False,
                ),
            ),
            (
                "protocol",
                DropdownChoice(
                    title=_("Protocol"),
                    choices=[
                        ("http", "HTTP"),
                        ("https", "HTTPS"),
                    ],
                    default_value="https",
                ),
            ),
            (
                "port",
                Integer(
                    title=_("Port"),
                    help=_(
                        "Use this option to query a port which is different from standard port 9200."
                    ),
                    default_value=9200,
                ),
            ),
            (
                "infos",
                ListChoice(
                    title=_("Informations to query"),
                    help=_(
                        "Defines what information to query. "
                        "Checks for Cluster, Indices and Shard statistics follow soon."
                    ),
                    choices=[
                        ("cluster_health", _("Cluster health")),
                        ("nodes", _("Node statistics")),
                        ("stats", _("Cluster, Indices and Shard statistics")),
                    ],
                    default_value=["cluster_health", "nodes", "stats"],
                    allow_empty=False,
                ),
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_elasticsearch(),
        group=RulespecGroupDatasourceProgramsApps,
        name="special_agents:elasticsearch",
        valuespec=_valuespec_special_agents_elasticsearch,
    )
)
