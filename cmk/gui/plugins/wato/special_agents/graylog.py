#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common import RulespecGroupDatasourceProgramsApps
from cmk.gui.plugins.wato.utils import HostRulespec, IndividualOrStoredPassword, rulespec_registry
from cmk.gui.valuespec import Age, Dictionary, DropdownChoice, ListChoice, NetworkPort, TextInput
from cmk.gui.watolib.rulespecs import Rulespec


def _factory_default_special_agents_graylog():
    # No default, do not use setting if no rule matches
    return Rulespec.FACTORY_DEFAULT_UNUSED


def _valuespec_special_agents_graylog():
    return Dictionary(
        title=_("Graylog"),
        help=_("Requests node, cluster and indice data from a Graylog instance."),
        optional_keys=["port", "source_since", "alerts_since", "events_since"],
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
                IndividualOrStoredPassword(
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
                NetworkPort(
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
                "source_since",
                Age(
                    title=_("Time for coverage of sources"),
                    help=_(
                        "If you choose to query for the total number of messages in a specific timeframe, use "
                        "this option to set the timeframe. The check will output the total number of messages received "
                        "in this given timeframe."
                    ),
                    default_value=1800,
                ),
            ),
            (
                "alerts_since",
                Age(
                    title=_("Time for coverage of alerts"),
                    help=_(
                        "If you choose to query for the total number of alerts in a specific timeframe, use "
                        "this option to set the timeframe. The check will output the total number of alerts received "
                        "in this given timeframe."
                    ),
                    default_value=1800,
                ),
            ),
            (
                "events_since",
                Age(
                    title=_("Time for coverage of events"),
                    help=_(
                        "If you choose to query for the total number of events in a specific timeframe, use "
                        "this option to set the timeframe. The check will output the total number of events received "
                        "in this given timeframe."
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
                        ("events", _("Events")),
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
                        "events",
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
