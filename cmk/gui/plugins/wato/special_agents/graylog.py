#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common import RulespecGroupDatasourceProgramsApps
from cmk.gui.plugins.wato.utils import HostRulespec, PasswordFromStore, rulespec_registry
from cmk.gui.valuespec import Age, Dictionary, DropdownChoice, Integer, ListChoice, TextInput
from cmk.gui.watolib.rulespecs import Rulespec


def _factory_default_special_agents_graylog():
    # No default, do not use setting if no rule matches
    return Rulespec.FACTORY_DEFAULT_UNUSED


def _valuespec_special_agents_graylog():
    return Dictionary(
        title=_("Graylog"),
        help=_("Requests node, cluster and indice data from a Graylog instance."),
        optional_keys=["port"],
        elements=[
            (
                "instance",
                TextInput(
                    title=_("Graylog instance to query"),
                    help=_(
                        "Use this option to set which instance should be "
                        "checked by the special agent. Please add the "
                        "hostname here, eg. my_graylog.com."
                    ),
                    size=32,
                    allow_empty=False,
                ),
            ),
            (
                "user",
                TextInput(
                    title=_("Username"),
                    help=_(
                        "The username that should be used for accessing the "
                        "Graylog API. Has to have read permissions at least."
                    ),
                    size=32,
                    allow_empty=False,
                ),
            ),
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
                        "Use this option to query a port which is different from standard port 443."
                    ),
                    default_value=443,
                ),
            ),
            (
                "since",
                Age(
                    title=_("Time for coverage of failures"),
                    help=_(
                        "If you choose to query for failed index operations, use "
                        "this option to set the timeframe in which failures "
                        "should be covered. The check will output the total "
                        "number of failures and the number of failures in this "
                        "given timeframe."
                    ),
                    default_value=1800,
                ),
            ),
            (
                "sections",
                ListChoice(
                    title=_("Information to query"),
                    help=_("Defines what information to query."),
                    choices=[
                        ("alerts", _("Alarms")),
                        ("cluster_stats", _("Cluster statistics")),
                        ("cluster_traffic", _("Cluster traffic statistics")),
                        ("failures", _("Failed index operations")),
                        ("jvm", _("JVM heap size")),
                        ("license", _("License state")),
                        ("messages", _("Message count")),
                        ("nodes", _("Nodes")),
                        ("sidecars", _("Sidecars")),
                        ("sources", _("Sources")),
                        ("streams", _("Streams")),
                    ],
                    default_value=[
                        "alerts",
                        "cluster_stats",
                        "cluster_traffic",
                        "failures",
                        "jvm",
                        "license",
                        "messages",
                        "nodes",
                        "sidecars",
                        "sources",
                        "streams",
                    ],
                    allow_empty=False,
                ),
            ),
            (
                "display_node_details",
                DropdownChoice(
                    title=_("Display node details on"),
                    help=_(
                        "The node details can be displayed either on the "
                        "queried host or the Graylog node."
                    ),
                    choices=[
                        ("host", _("The queried Graylog host")),
                        ("node", _("The Graylog node")),
                    ],
                    default_value="host",
                ),
            ),
            (
                "display_sidecar_details",
                DropdownChoice(
                    title=_("Display sidecar details on"),
                    help=_(
                        "The sidecar details can be displayed either on the "
                        "queried host or the sidecar host."
                    ),
                    choices=[
                        ("host", _("The queried Graylog host")),
                        ("sidecar", _("The sidecar host")),
                    ],
                    default_value="host",
                ),
            ),
            (
                "display_source_details",
                DropdownChoice(
                    title=_("Display source details on"),
                    help=_(
                        "The source details can be displayed either on the "
                        "queried host or the source host."
                    ),
                    choices=[
                        ("host", _("The queried Graylog host")),
                        ("source", _("The source host")),
                    ],
                    default_value="host",
                ),
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_graylog(),
        group=RulespecGroupDatasourceProgramsApps,
        name="special_agents:graylog",
        valuespec=_valuespec_special_agents_graylog,
    )
)
