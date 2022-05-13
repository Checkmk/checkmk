#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.i18n import _
from cmk.gui.plugins.wato.active_checks.common import RulespecGroupIntegrateOtherServices
from cmk.gui.plugins.wato.utils import (
    HostRulespec,
    PasswordFromStore,
    PluginCommandLine,
    rulespec_registry,
)
from cmk.gui.valuespec import (
    Age,
    Alternative,
    Dictionary,
    DropdownChoice,
    FixedValue,
    Integer,
    ListOfStrings,
    TextInput,
    Tuple,
)


def _valuespec_custom_checks():
    return Dictionary(
        title=_("Integrate Nagios plugins"),
        help=_(
            'With this ruleset you can configure "classical Monitoring checks" '
            "to be executed directly on your monitoring server. These checks "
            "will not use Check_MK. It is also possible to configure passive "
            "checks that are fed with data from external sources via the "
            "command pipe of the monitoring core."
        )
        + _('This option can only be used with the permission "Can add or modify executables".'),
        elements=[
            (
                "service_description",
                TextInput(
                    title=_("Service description"),
                    help=_(
                        "Please make sure that this is unique per host "
                        "and does not collide with other services."
                    ),
                    allow_empty=False,
                    default_value=_("Customcheck"),
                ),
            ),
            (
                "command_line",
                PluginCommandLine(),
            ),
            (
                "command_name",
                TextInput(
                    title=_("Internal command name"),
                    help=_(
                        "If you want, you can specify a name that will be used "
                        "in the <tt>define command</tt> section for these checks. This "
                        "allows you to a assign a custom PNP template for the performance "
                        "data of the checks. If you omit this, then <tt>check-mk-custom</tt> "
                        "will be used."
                    ),
                    size=32,
                ),
            ),
            (
                "has_perfdata",
                FixedValue(
                    value=True,
                    title=_("Performance data"),
                    totext=_("process performance data"),
                ),
            ),
            (
                "freshness",
                Dictionary(
                    title=_("Check freshness"),
                    help=_(
                        "Freshness checking is only useful for passive checks when the staleness feature "
                        "is not enough for you. It changes the state of a check to a configurable other state "
                        "when the check results are not arriving in time. Staleness will still grey out the "
                        "test after the corrsponding interval. If you don't want that, you might want to adjust "
                        "the staleness interval as well. The staleness interval is calculated from the normal "
                        "check interval multiplied by the staleness value in the <tt>Global Settings</tt>. "
                        "The normal check interval can be configured in a separate rule for your check."
                    ),
                    optional_keys=False,
                    elements=[
                        (
                            "interval",
                            Integer(
                                title=_("Expected update interval"),
                                label=_("Updates are expected at least every"),
                                unit=_("minutes"),
                                minvalue=1,
                                default_value=10,
                            ),
                        ),
                        (
                            "state",
                            DropdownChoice(
                                title=_("State in case of absent updates"),
                                choices=[
                                    (0, _("OK")),
                                    (1, _("WARN")),
                                    (2, _("CRIT")),
                                    (3, _("UNKNOWN")),
                                ],
                                default_value=3,
                            ),
                        ),
                        (
                            "output",
                            TextInput(
                                title=_("Plugin output in case of absent updates"),
                                size=40,
                                allow_empty=False,
                                default_value=_("Check result did not arrive in time"),
                            ),
                        ),
                    ],
                ),
            ),
        ],
        required_keys=["service_description"],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupIntegrateOtherServices,
        match_type="all",
        name="custom_checks",
        valuespec=_valuespec_custom_checks,
    )
)


def _valuespec_active_checks_by_ssh():
    return Tuple(
        title=_("Check via SSH service"),
        help=_("Checks via SSH. "),
        elements=[
            TextInput(
                title=_("Command"),
                help=_("Command to execute on remote host."),
                allow_empty=False,
                size=50,
            ),
            Dictionary(
                title=_("Optional parameters"),
                elements=[
                    (
                        "description",
                        TextInput(
                            title=_("Service Description"),
                            help=_(
                                "Must be unique for every host. Defaults to command that is executed."
                            ),
                            size=50,
                        ),
                    ),
                    (
                        "hostname",
                        TextInput(
                            title=_("DNS Hostname or IP address"),
                            default_value="$HOSTADDRESS$",
                            allow_empty=False,
                            help=_(
                                "You can specify a hostname or IP address different from IP address "
                                "of the host as configured in your host properties."
                            ),
                        ),
                    ),
                    (
                        "port",
                        Integer(
                            title=_("SSH Port"),
                            help=_("Default is 22."),
                            minvalue=1,
                            maxvalue=65535,
                            default_value=22,
                        ),
                    ),
                    (
                        "ip_version",
                        Alternative(
                            title=_("IP-Version"),
                            elements=[
                                FixedValue(value="ipv4", totext="", title=_("IPv4")),
                                FixedValue(value="ipv6", totext="", title=_("IPv6")),
                            ],
                        ),
                    ),
                    (
                        "timeout",
                        Integer(
                            title=_("Seconds before connection times out"),
                            unit=_("sec"),
                            default_value=10,
                        ),
                    ),
                    (
                        "logname",
                        TextInput(
                            title=_("Username"), help=_("SSH user name on remote host"), size=30
                        ),
                    ),
                    (
                        "identity",
                        TextInput(
                            title=_("Keyfile"), help=_("Identity of an authorized key"), size=50
                        ),
                    ),
                    (
                        "accept_new_host_keys",
                        FixedValue(
                            value=True,
                            title=_("Enable automatic host key acceptance"),
                            help=_(
                                "This will automatically accept hitherto-unseen keys"
                                "but will refuse connections for changed or invalid hostkeys"
                            ),
                            totext=_(
                                "Automatically stores the host key with no manual input requirement"
                            ),
                        ),
                    ),
                ],
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupIntegrateOtherServices,
        match_type="all",
        name="active_checks:by_ssh",
        valuespec=_valuespec_active_checks_by_ssh,
    )
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
