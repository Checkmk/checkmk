#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.active_checks.common import RulespecGroupIntegrateOtherServices
from cmk.gui.plugins.wato.utils import HostRulespec, PasswordFromStore, rulespec_registry
from cmk.gui.valuespec import (
    Age,
    Dictionary,
    DropdownChoice,
    Integer,
    ListOfStrings,
    TextInput,
    Tuple,
)


def _valuespec_active_checks_elasticsearch_query():
    return Dictionary(
        required_keys=["svc_item", "pattern", "timerange"],
        title=_("Query elasticsearch logs"),
        help=_("You can search indices for defined patterns in defined fieldnames."),
        elements=[
            (
                "svc_item",
                TextInput(
                    title=_("Item suffix"),
                    help=_(
                        "Here you can define what service description (item) is "
                        "used for the created service. The resulting item "
                        "is always prefixed with 'Elasticsearch Query'."
                    ),
                    allow_empty=False,
                    size=16,
                ),
            ),
            (
                "hostname",
                TextInput(
                    title=_("DNS hostname or IP address"),
                    help=_(
                        "You can specify a hostname or IP address different from the IP address "
                        "of the host this check will be assigned to."
                    ),
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
                    help=_("Here you can define which protocol to use, default is https."),
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
                "pattern",
                TextInput(
                    title=_("Search pattern"),
                    help=_(
                        "Here you can define what search pattern should be used. "
                        "You can use Kibana query language as described "
                        '<a href="https://www.elastic.co/guide/en/kibana/current/kuery-query.html"'
                        'target="_blank">here</a>. To optimize search speed, use defined indices and fields '
                        "otherwise all indices and fields will be searched."
                    ),
                    allow_empty=False,
                    size=32,
                ),
            ),
            (
                "index",
                ListOfStrings(
                    title=_("Indices to query"),
                    help=_(
                        "Here you can define what index should be queried "
                        "for the defined search. You can query one or "
                        "multiple indices. Without this option all indices "
                        "are queried. If you want to speed up your search, "
                        "use definded indices."
                    ),
                    orientation="horizontal",
                    allow_empty=False,
                    size=48,
                ),
            ),
            (
                "fieldname",
                ListOfStrings(
                    title=_("Fieldnames to query"),
                    help=_(
                        "Here you can define fieldnames that should be used "
                        "in the search. Regexp query is allowed as described "
                        '<a href="https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-regexp-query.html"'
                        'target="_blank">here</a>. If you want to speed up your search, '
                        "use defined indices."
                    ),
                    allow_empty=False,
                    orientation="horizontal",
                    size=32,
                ),
            ),
            (
                "timerange",
                Age(
                    title=_("Timerange"),
                    help=_(
                        "Here you can define the timerange to query, eg. the last x minutes from now. "
                        "The query will then check for the count of log messages in the defined range. "
                        "Default is 1 minute."
                    ),
                    display=["days", "hours", "minutes"],
                    default_value=60,
                ),
            ),
            (
                "count",
                Tuple(
                    title=_("Thresholds on message count"),
                    elements=[
                        Integer(
                            title=_("Warning at or above"),
                            unit=_("log messages"),
                        ),
                        Integer(
                            title=_("Critical at or above"),
                            unit=_("log messages"),
                        ),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupIntegrateOtherServices,
        match_type="all",
        name="active_checks:elasticsearch_query",
        valuespec=_valuespec_active_checks_elasticsearch_query,
    )
)
