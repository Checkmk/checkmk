#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy
from typing import Any, Mapping, Union

import cmk.gui.mkeventd as mkeventd
from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    HostRulespec,
    IndividualOrStoredPassword,
    PasswordFromStore,
    PluginCommandLine,
    rulespec_group_registry,
    rulespec_registry,
    RulespecGroup,
)
from cmk.gui.valuespec import (
    Age,
    Alternative,
    CascadingDropdown,
    Checkbox,
    Dictionary,
    DropdownChoice,
    EmailAddress,
    FixedValue,
    Float,
    Hostname,
    Integer,
    ListOf,
    ListOfStrings,
    Optional,
    Password,
    Percentage,
    RegExp,
    TextAreaUnicode,
    TextInput,
    Transform,
    Tuple,
)


@rulespec_group_registry.register
class RulespecGroupIntegrateOtherServices(RulespecGroup):
    @property
    def name(self):
        return "custom_checks"

    @property
    def title(self):
        return _("Other services")

    @property
    def help(self):
        return _(
            "This services are provided by so called active checks. "
            "You can also integrate custom nagios plugins."
        )


@rulespec_group_registry.register
class RulespecGroupActiveChecks(RulespecGroup):
    @property
    def name(self):
        return "activechecks"

    @property
    def title(self):
        return _("HTTP, TCP, Email, ...")

    @property
    def help(self):
        return _(
            "Rules to add [active_checks|network services] like HTTP and TCP to the "
            "monitoring. The services are provided by so called active checks that allow "
            "you to monitor network services directly from the outside."
        )


# These elements are also used in check_parameters.py
def check_icmp_params():
    return [
        (
            "rta",
            Tuple(
                title=_("Round trip average"),
                elements=[
                    Float(title=_("Warning if above"), unit="ms", default_value=200.0),
                    Float(title=_("Critical if above"), unit="ms", default_value=500.0),
                ],
            ),
        ),
        (
            "loss",
            Tuple(
                title=_("Packet loss"),
                help=_(
                    "When the percentage of lost packets is equal or greater then "
                    "this level, then the according state is triggered. The default for critical "
                    "is 100%. That means that the check is only critical if <b>all</b> packets "
                    "are lost."
                ),
                elements=[
                    Percentage(title=_("Warning at"), default_value=80.0),
                    Percentage(title=_("Critical at"), default_value=100.0),
                ],
            ),
        ),
        (
            "packets",
            Integer(
                title=_("Number of packets"),
                help=_(
                    "Number ICMP echo request packets to send to the target host on each "
                    "check execution. All packets are sent directly on check execution. Afterwards "
                    "the check waits for the incoming packets."
                ),
                minvalue=1,
                maxvalue=20,
                default_value=5,
            ),
        ),
        (
            "timeout",
            Integer(
                title=_("Total timeout of check"),
                help=_(
                    "After this time (in seconds) the check is aborted, regardless "
                    "of how many packets have been received yet."
                ),
                minvalue=1,
            ),
        ),
    ]


def _imap_parameters():
    return Dictionary(
        title="IMAP",
        optional_keys=[],
        elements=[
            (
                "server",
                TextInput(
                    title=_("IMAP Server"),
                    allow_empty=False,
                    help=_(
                        "You can specify a hostname or IP address different from the IP address "
                        "of the host this check will be assigned to."
                    ),
                ),
            ),
            (
                "ssl",
                CascadingDropdown(
                    title=_("SSL Encryption"),
                    default_value=(False, 143),
                    choices=[
                        (
                            False,
                            _("Use no encryption"),
                            Optional(
                                Integer(
                                    default_value=143,
                                ),
                                title=_("TCP Port"),
                                help=_("By default the standard IMAP Port 143 is used."),
                            ),
                        ),
                        (
                            True,
                            _("Encrypt IMAP communication using SSL"),
                            Optional(
                                Integer(
                                    default_value=993,
                                ),
                                title=_("TCP Port"),
                                help=_("By default the standard IMAP/SSL Port 993 is used."),
                            ),
                        ),
                    ],
                ),
            ),
            (
                "auth",
                Tuple(
                    title=_("Authentication"),
                    elements=[
                        TextInput(title=_("Username"), allow_empty=False, size=24),
                        IndividualOrStoredPassword(title=_("Password"), allow_empty=False, size=12),
                    ],
                ),
            ),
        ],
    )


def _pop3_parameters():
    return Dictionary(
        optional_keys=["server"],
        elements=[
            (
                "server",
                TextInput(
                    title=_("POP3 Server"),
                    allow_empty=False,
                    help=_(
                        "You can specify a hostname or IP address different from the IP address "
                        "of the host this check will be assigned to."
                    ),
                ),
            ),
            (
                "ssl",
                CascadingDropdown(
                    title=_("SSL Encryption"),
                    default_value=(False, 110),
                    choices=[
                        (
                            False,
                            _("Use no encryption"),
                            Optional(
                                Integer(
                                    default_value=110,
                                ),
                                title=_("TCP Port"),
                                help=_("By default the standard POP3 Port 110 is used."),
                            ),
                        ),
                        (
                            True,
                            _("Encrypt POP3 communication using SSL"),
                            Optional(
                                Integer(
                                    default_value=995,
                                ),
                                title=_("TCP Port"),
                                help=_("By default the standard POP3/SSL Port 995 is used."),
                            ),
                        ),
                    ],
                ),
            ),
            (
                "auth",
                Tuple(
                    title=_("Authentication"),
                    elements=[
                        TextInput(title=_("Username"), allow_empty=False, size=24),
                        IndividualOrStoredPassword(title=_("Password"), allow_empty=False, size=12),
                    ],
                ),
            ),
        ],
    )


def _mail_receiving_params():
    return [
        (
            "fetch",
            CascadingDropdown(
                title=_("Mail Receiving"),
                choices=[
                    ("IMAP", _("IMAP"), _imap_parameters()),
                    ("POP3", _("POP3"), _pop3_parameters()),
                ],
            ),
        ),
    ]


def _valuespec_active_checks_ssh():
    return Dictionary(
        title=_("Check SSH service"),
        help=_("This rulset allow you to configure a SSH check for a host"),
        elements=[
            (
                "description",
                TextInput(
                    title=_("Service Description"),
                ),
            ),
            (
                "port",
                Integer(
                    title=_("TCP port number"),
                    default_value=22,
                ),
            ),
            (
                "timeout",
                Integer(
                    title=_("Connect Timeout"),
                    help=_("Seconds before connection times out"),
                    default_value=10,
                ),
            ),
            (
                "remote_version",
                TextInput(
                    title=_("Version of Server"),
                    help=_(
                        "Warn if string doesn't match expected server version (ex: OpenSSH_3.9p1)"
                    ),
                ),
            ),
            (
                "remote_protocol",
                TextInput(
                    title=_("Protocol of Server"),
                    help=_("Warn if protocol doesn't match expected protocol version (ex: 2.0)"),
                ),
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupIntegrateOtherServices,
        match_type="all",
        name="active_checks:ssh",
        valuespec=_valuespec_active_checks_ssh,
    )
)


def _valuespec_active_checks_icmp():
    return Dictionary(
        title=_("Check hosts with PING (ICMP Echo Request)"),
        help=_(
            "This ruleset allows you to configure explicit PING monitoring of hosts. "
            "Usually a PING is being used as a host check, so this is not neccessary. "
            "There are some situations, however, where this can be useful. One of them "
            "is when using the Check_MK Micro Core with SMART Ping and you want to "
            "track performance data of the PING to some hosts, nevertheless."
        ),
        elements=[
            (
                "description",
                TextInput(
                    title=_("Service Description"),
                    allow_empty=False,
                    default_value="PING",
                ),
            ),
            (
                "address",
                CascadingDropdown(
                    title=_("Alternative address to ping"),
                    help=_(
                        "If you omit this setting then the configured IP address of that host "
                        "will be pinged. In the host configuration you can provide additional "
                        "addresses besides the main IP address (additional IP addresses section). "
                        "In this option you can select which set of addresses you want to include "
                        'for this check. "Ping additional IP addresses" will omit the host '
                        'configured main address while the "Ping all addresses" option will '
                        "include both the main and additional addresses."
                    ),
                    orientation="horizontal",
                    choices=[
                        ("address", _("Ping the normal IP address")),
                        ("alias", _("Use the alias as DNS name / IP address")),
                        (
                            "explicit",
                            _("Ping the following explicit address / DNS name"),
                            Hostname(),
                        ),
                        ("all_ipv4addresses", _("Ping all IPv4 addresses")),
                        ("all_ipv6addresses", _("Ping all IPv6 addresses")),
                        ("additional_ipv4addresses", _("Ping additional IPv4 addresses")),
                        ("additional_ipv6addresses", _("Ping additional IPv6 addresses")),
                        (
                            "indexed_ipv4address",
                            _("Ping IPv4 address identified by its index"),
                            Integer(default_value=1),
                        ),
                        (
                            "indexed_ipv6address",
                            _("Ping IPv6 address identified by its index"),
                            Integer(default_value=1),
                        ),
                    ],
                ),
            ),
            (
                "min_pings",
                Integer(
                    title=_("Number of positive responses required for OK state"),
                    help=_(
                        "When pinging multiple addresses, failure to ping one of the "
                        "provided addresses will lead to a Crit status of the service. "
                        "This option allows to specify the minimum number of successful "
                        "pings which will still classify the service as OK. The smallest "
                        "number is 1 and the maximum number should be (number of addresses - 1). "
                        "A number larger than the suggested number will always lead to a "
                        "Crit Status. One must also select a suitable option from the "
                        '"Alternative address to ping" above.'
                    ),
                    minvalue=1,
                ),
            ),
        ]
        + check_icmp_params(),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupActiveChecks,
        match_type="all",
        name="active_checks:icmp",
        valuespec=_valuespec_active_checks_icmp,
    )
)


# Several active checks just had crit levels as one integer
def transform_cert_days(cert_days):
    if not isinstance(cert_days, tuple):
        return (cert_days, 0)
    return cert_days


def _valuespec_active_checks_ftp():
    return Transform(
        Dictionary(
            elements=[
                (
                    "port",
                    Integer(
                        title=_("Portnumber"),
                        default_value=21,
                    ),
                ),
                (
                    "response_time",
                    Tuple(
                        title=_("Expected response time"),
                        elements=[
                            Float(title=_("Warning if above"), unit="ms", default_value=100.0),
                            Float(title=_("Critical if above"), unit="ms", default_value=200.0),
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
                    "refuse_state",
                    DropdownChoice(
                        title=_("State for connection refusal"),
                        choices=[
                            ("crit", _("CRITICAL")),
                            ("warn", _("WARNING")),
                            ("ok", _("OK")),
                        ],
                    ),
                ),
                ("send_string", TextInput(title=_("String to send"), size=30)),
                (
                    "expect",
                    ListOfStrings(
                        title=_("Strings to expect in response"),
                        orientation="horizontal",
                        valuespec=TextInput(size=30),
                    ),
                ),
                (
                    "ssl",
                    FixedValue(
                        value=True, totext=_("use SSL"), title=_("Use SSL for the connection.")
                    ),
                ),
                (
                    "cert_days",
                    Transform(
                        Tuple(
                            title=_("SSL certificate validation"),
                            help=_("Minimum number of days a certificate has to be valid"),
                            elements=[
                                Integer(title=_("Warning at or below"), minvalue=0, unit=_("days")),
                                Integer(
                                    title=_("Critical at or below"), minvalue=0, unit=_("days")
                                ),
                            ],
                        ),
                        forth=transform_cert_days,
                    ),
                ),
            ]
        ),
        forth=lambda x: isinstance(x, tuple) and x[1] or x,
        title=_("Check FTP Service"),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupActiveChecks,
        match_type="all",
        name="active_checks:ftp",
        valuespec=_valuespec_active_checks_ftp,
    )
)


def _valuespec_active_checks_sftp():
    return Tuple(
        title=_("Check SFTP Service"),
        help=_(
            "Check functionality of a SFTP server. You can use the default values for putting or getting "
            "a file. This file will then be created for the test and deleted afterwards. It will of course not "
            "deleted if it was not created by this active check."
        ),
        elements=[
            TextInput(title=_("Hostname"), allow_empty=False),
            TextInput(title=_("Username"), allow_empty=False),
            IndividualOrStoredPassword(title=_("Password"), allow_empty=False),
            Dictionary(
                elements=[
                    (
                        "description",
                        TextInput(title=_("Service Description"), default_value="SFTP", size=30),
                    ),
                    ("port", Integer(title=_("Port"), default_value=22)),
                    ("timeout", Integer(title=_("Timeout"), default_value=10)),
                    (
                        "timestamp",
                        TextInput(
                            title=_("Timestamp of a remote file"),
                            size=30,
                            help=_(
                                "Show timestamp of a given file. You only need to specify the "
                                "relative path of the remote file. Examples: 'myDirectory/testfile' "
                                " or 'testfile'"
                            ),
                        ),
                    ),
                    (
                        "put",
                        Tuple(
                            title=_("Put file to SFTP server"),
                            elements=[
                                TextInput(
                                    title=_("Local file"),
                                    size=30,
                                    default_value="tmp/check_mk_testfile",
                                    help=_(
                                        "Local path including filename. Base directory for this relative path "
                                        "will be the home directory of your site. The testfile will be created "
                                        "if it does not exist. Examples: 'tmp/testfile' (file will be located in "
                                        "$OMD_ROOT/tmp/testfile )"
                                    ),
                                ),
                                TextInput(
                                    title=_("Remote destination"),
                                    size=30,
                                    default_value="",
                                    help=_(
                                        "Remote path where to put the file. If you leave this empty, the file will be placed "
                                        "in the home directory of the user. Example: 'myDirectory' "
                                    ),
                                ),
                            ],
                        ),
                    ),
                    (
                        "get",
                        Tuple(
                            title=_("Get file from SFTP server"),
                            elements=[
                                TextInput(
                                    title=_("Remote file"),
                                    size=30,
                                    default_value="check_mk_testfile",
                                    help=_(
                                        "Remote path including filename "
                                        "(e.g. 'testfile'). If you also enabled "
                                        "'Put file to SFTP server', you can use the same file for both tests."
                                    ),
                                ),
                                TextInput(
                                    title=_("Local destination"),
                                    size=30,
                                    default_value="tmp",
                                    help=_(
                                        "Local path where to put the downloaded file "
                                        "(e.g. 'tmp' )."
                                    ),
                                ),
                            ],
                        ),
                    ),
                ]
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupActiveChecks,
        match_type="all",
        name="active_checks:sftp",
        valuespec=_valuespec_active_checks_sftp,
    )
)


def _transform_check_dns_settings(params: Mapping[str, Any]) -> Mapping[str, Any]:
    """
    >>> _transform_check_dns_settings({'expected_address': '1.2.3.4,C0FE::FE11'})
    {'expect_all_addresses': True, 'expected_addresses_list': ['1.2.3.4', 'C0FE::FE11']}
    >>> _transform_check_dns_settings({'expected_address': ['A,B', 'C']})
    {'expect_all_addresses': True, 'expected_addresses_list': ['A', 'B', 'C']}

    """
    legacy_addresses = params.get("expected_address")
    if legacy_addresses is None:
        return params

    return {
        "expect_all_addresses": True,
        "expected_addresses_list": (
            legacy_addresses.split(",")
            if isinstance(legacy_addresses, str)
            else sum((entry.split(",") for entry in legacy_addresses), [])
        ),
        **{k: v for k, v in params.items() if k != "expected_address"},
    }


def _valuespec_active_checks_dns():
    return Tuple(
        title=_("Check DNS service"),
        help=_(
            "Check the resolution of a hostname into an IP address by a DNS server. "
            "This check uses <tt>check_dns</tt> from the standard Nagios plugins."
        ),
        elements=[
            TextInput(
                title=_("Queried Hostname or IP address"),
                allow_empty=False,
                help=_("The name or IPv4 address you want to query"),
            ),
            Transform(
                Dictionary(
                    title=_("Optional parameters"),
                    elements=[
                        (
                            "name",
                            TextInput(
                                title=_("Alternative Service description"),
                                help=_(
                                    "The service description will be this name instead <i>DNS Servername</i>"
                                ),
                            ),
                        ),
                        (
                            "server",
                            Alternative(
                                title=_("DNS Server"),
                                elements=[
                                    FixedValue(
                                        value=None,
                                        totext=_("this host"),
                                        title=_("Use this host as a DNS server for the lookup"),
                                    ),
                                    TextInput(
                                        title=_("Specify DNS Server"),
                                        allow_empty=False,
                                        help=_(
                                            "Optional DNS server you want to use for the lookup"
                                        ),
                                    ),
                                    FixedValue(
                                        value="default DNS server",
                                        totext=_("default DNS server"),
                                        title=_("Use default DNS server"),
                                    ),
                                ],
                            ),
                        ),
                        (
                            "expect_all_addresses",
                            DropdownChoice(
                                title=_("Address matching"),
                                choices=[
                                    (True, _("Expect all of the addresses")),
                                    (False, _("Expect at least one of the addresses")),
                                ],
                            ),
                        ),
                        (
                            "expected_addresses_list",
                            ListOfStrings(
                                title=_("Expected DNS answers"),
                                help=_(
                                    "List all allowed expected answers here. If query for an "
                                    "IP address then the answer will be host names, that end "
                                    "with a dot."
                                ),
                            ),
                        ),
                        (
                            "expected_authority",
                            FixedValue(
                                value=True,
                                title=_("Expect Authoritative DNS Server"),
                                totext=_("Expect Authoritative"),
                            ),
                        ),
                        (
                            "response_time",
                            Tuple(
                                title=_("Expected response time"),
                                elements=[
                                    Float(
                                        title=_("Warning if above"), unit=_("sec"), default_value=1
                                    ),
                                    Float(
                                        title=_("Critical if above"), unit=_("sec"), default_value=2
                                    ),
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
                    ],
                ),
                forth=_transform_check_dns_settings,
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupActiveChecks,
        match_type="all",
        name="active_checks:dns",
        valuespec=_valuespec_active_checks_dns,
    )
)


def transform_check_sql_perfdata(perfdata: Union[str, bool]) -> str:
    if isinstance(perfdata, str):
        return perfdata
    return "performance_data"


def _valuespec_active_checks_sql() -> Dictionary:
    return Dictionary(
        title=_("Check SQL Database"),
        help=_(
            "This check connects to the specified database, sends a custom SQL-statement "
            "or starts a procedure, and checks that the result has a defined format "
            "containing three columns, a number, a text, and performance data. Upper or "
            "lower levels may be defined here.  If they are not defined the number is taken "
            "as the state of the check.  If a procedure is used, input parameters of the "
            "procedures may by given as comma separated list. "
            "This check uses the active check <tt>check_sql</tt>."
        ),
        optional_keys=["levels", "levels_low", "perfdata", "port", "procedure", "host"],
        elements=[
            (
                "description",
                TextInput(
                    title=_("Service Description"),
                    help=_("The name of this active service to be displayed."),
                    allow_empty=False,
                ),
            ),
            (
                "dbms",
                DropdownChoice(
                    title=_("Type of Database"),
                    choices=[
                        ("mysql", _("MySQL")),
                        ("postgres", _("PostgreSQL")),
                        ("mssql", _("MSSQL")),
                        ("oracle", _("Oracle")),
                        ("db2", _("DB2")),
                    ],
                    default_value="postgres",
                ),
            ),
            (
                "port",
                Integer(
                    title=_("Database Port"),
                    help=_("The port the DBMS listens to"),
                ),
            ),
            (
                "name",
                TextInput(
                    title=_("Database Name"),
                    help=_("The name of the database on the DBMS"),
                    allow_empty=False,
                ),
            ),
            (
                "user",
                TextInput(
                    title=_("Database User"),
                    help=_("The username used to connect to the database"),
                    allow_empty=False,
                ),
            ),
            (
                "password",
                IndividualOrStoredPassword(
                    title=_("Database Password"),
                    help=_("The password used to connect to the database"),
                    allow_empty=False,
                ),
            ),
            (
                "sql",
                Transform(
                    TextAreaUnicode(
                        title=_("Query or SQL statement"),
                        help=_(
                            "The SQL-statement or procedure name which is executed on the DBMS. It must return "
                            "a result table with one row and at least two columns. The first column must be "
                            "an integer and is interpreted as the state (0 is OK, 1 is WARN, 2 is CRIT). "
                            "Alternatively the first column can be interpreted as number value and you can "
                            "define levels for this number. The "
                            "second column is used as check output. The third column is optional and can "
                            "contain performance data."
                        ),
                        allow_empty=False,
                        monospaced=True,
                    ),
                    # Former Alternative(Text, Alternative(FileUpload, Text)) based implementation
                    # would save a string or a tuple with a string or a binary array as third element
                    # which would then be turned into a string.
                    # Just make all this a string
                    forth=lambda old_val: [
                        elem.decode() if isinstance(elem, bytes) else str(elem)
                        for elem in ((old_val[-1] if isinstance(old_val, tuple) else old_val),)
                    ][0],
                ),
            ),
            (
                "procedure",
                Dictionary(
                    optional_keys=["input"],
                    title=_("Use procedure call instead of SQL statement"),
                    help=_(
                        "If you activate this option, a name of a stored "
                        "procedure is used instead of an SQL statement. "
                        "The procedure should return one output variable, "
                        "which is evaluated in the check. If input parameters "
                        "are required, they may be specified below."
                    ),
                    elements=[
                        (
                            "useprocs",
                            FixedValue(
                                value=True,
                                totext=_("procedure call is used"),
                            ),
                        ),
                        (
                            "input",
                            TextInput(
                                title=_("Input Parameters"),
                                allow_empty=True,
                                help=_(
                                    "Input parameters, if required by the database procedure. "
                                    "If several parameters are required, use commas to separate them."
                                ),
                            ),
                        ),
                    ],
                ),
            ),
            (
                "levels",
                Tuple(
                    title=_("Upper levels for first output item"),
                    elements=[Float(title=_("Warning at")), Float(title=_("Critical at"))],
                ),
            ),
            (
                "levels_low",
                Tuple(
                    title=_("Lower levels for first output item"),
                    elements=[Float(title=_("Warning below")), Float(title=_("Critical below"))],
                ),
            ),
            (
                "perfdata",
                Transform(
                    TextInput(
                        title=_("Performance Data"),
                        help=_("Store output value into RRD database in a metric with this name."),
                        default_value="performance_data",
                        allow_empty=False,
                    ),
                    forth=transform_check_sql_perfdata,
                ),
            ),
            (
                "host",
                TextInput(
                    title=_("DNS hostname or IP address"),
                    help=_("This defaults to the host for which the active check is configured."),
                ),
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupActiveChecks,
        match_type="all",
        name="active_checks:sql",
        valuespec=_valuespec_active_checks_sql,
    )
)


def _valuespec_active_checks_tcp():
    return Tuple(
        title=_("Check TCP port connection"),
        help=_(
            "This check tests the connection to a TCP port. It uses "
            "<tt>check_tcp</tt> from the standard Nagios plugins."
        ),
        elements=[
            Integer(title=_("TCP Port"), minvalue=1, maxvalue=65535),
            Dictionary(
                title=_("Optional parameters"),
                elements=[
                    (
                        "svc_description",
                        TextInput(
                            title=_("Service description"),
                            allow_empty=False,
                            help=_(
                                "Here you can specify a service description. "
                                "If this parameter is not set, the service is named <tt>TCP Port [PORT NUMBER]</tt>"
                            ),
                        ),
                    ),
                    (
                        "hostname",
                        TextInput(
                            title=_("DNS Hostname"),
                            allow_empty=False,
                            help=_(
                                "If you specify a hostname here, then a dynamic DNS lookup "
                                "will be done instead of using the IP address of the host "
                                "as configured in your host properties."
                            ),
                        ),
                    ),
                    (
                        "response_time",
                        Tuple(
                            title=_("Expected response time"),
                            elements=[
                                Float(title=_("Warning if above"), unit="ms", default_value=100.0),
                                Float(title=_("Critical if above"), unit="ms", default_value=200.0),
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
                        "refuse_state",
                        DropdownChoice(
                            title=_("State for connection refusal"),
                            choices=[
                                ("crit", _("CRITICAL")),
                                ("warn", _("WARNING")),
                                ("ok", _("OK")),
                            ],
                        ),
                    ),
                    ("send_string", TextInput(title=_("String to send"), size=30)),
                    (
                        "escape_send_string",
                        FixedValue(
                            value=True,
                            title=_(
                                "Expand <tt>\\n</tt>, <tt>\\r</tt> and <tt>\\t</tt> in the sent string"
                            ),
                            totext=_("expand escapes"),
                        ),
                    ),
                    (
                        "expect",
                        ListOfStrings(
                            title=_("Strings to expect in response"),
                            orientation="horizontal",
                            valuespec=TextInput(size=30),
                        ),
                    ),
                    (
                        "expect_all",
                        FixedValue(
                            value=True,
                            totext=_("expect all"),
                            title=_("Expect <b>all</b> of those strings in the response"),
                        ),
                    ),
                    (
                        "jail",
                        FixedValue(
                            value=True,
                            title=_("Hide response from socket"),
                            help=_(
                                "As soon as you configure expected strings in "
                                "the response the check will output the response - "
                                "as long as you do not hide it with this option"
                            ),
                            totext=_("hide response"),
                        ),
                    ),
                    (
                        "mismatch_state",
                        DropdownChoice(
                            title=_("State for expected string mismatch"),
                            choices=[
                                ("crit", _("CRITICAL")),
                                ("warn", _("WARNING")),
                                ("ok", _("OK")),
                            ],
                        ),
                    ),
                    (
                        "delay",
                        Integer(
                            title=_("Seconds to wait before polling"),
                            help=_(
                                "Seconds to wait between sending string and polling for response"
                            ),
                            unit=_("sec"),
                            default_value=0,
                        ),
                    ),
                    (
                        "maxbytes",
                        Integer(
                            title=_("Maximum number of bytes to receive"),
                            help=_(
                                "Close connection once more than this number of "
                                "bytes are received. Per default the number of "
                                "read bytes is not limited. This setting is only "
                                "used if you expect strings in the response."
                            ),
                            default_value=1024,
                        ),
                    ),
                    (
                        "ssl",
                        FixedValue(
                            value=True, totext=_("use SSL"), title=_("Use SSL for the connection.")
                        ),
                    ),
                    (
                        "cert_days",
                        Transform(
                            Tuple(
                                title=_("SSL certificate validation"),
                                help=_("Minimum number of days a certificate has to be valid"),
                                elements=[
                                    Integer(
                                        title=_("Warning at or below"), minvalue=0, unit=_("days")
                                    ),
                                    Integer(
                                        title=_("Critical at or below"), minvalue=0, unit=_("days")
                                    ),
                                ],
                            ),
                            forth=transform_cert_days,
                        ),
                    ),
                    (
                        "quit_string",
                        TextInput(
                            title=_("Final string to send"),
                            help=_(
                                "String to send server to initiate a clean close of "
                                "the connection"
                            ),
                            size=30,
                        ),
                    ),
                ],
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupActiveChecks,
        match_type="all",
        name="active_checks:tcp",
        valuespec=_valuespec_active_checks_tcp,
    )
)


def _valuespec_active_checks_uniserv():
    return Dictionary(
        title=_("Check uniserv service"),
        optional_keys=False,
        elements=[
            ("port", Integer(title=_("Port"))),
            (
                "service",
                TextInput(
                    title=_("Service Name"),
                    help=_(
                        "Enter the uniserve service name here (has nothing to do with service description)."
                    ),
                ),
            ),
            (
                "job",
                CascadingDropdown(
                    title=_("Mode of the Check"),
                    help=_(
                        "Choose, whether you just want to query the version number,"
                        " or if you want to check the response to an address query."
                    ),
                    choices=[
                        ("version", _("Check for Version")),
                        (
                            "address",
                            _("Check for an Address"),
                            Dictionary(
                                title=_("Address Check mode"),
                                optional_keys=False,
                                elements=[
                                    ("street", TextInput(title=_("Street name"))),
                                    ("street_no", Integer(title=_("Street number"))),
                                    ("city", TextInput(title=_("City name"))),
                                    (
                                        "search_regex",
                                        TextInput(
                                            title=_("Check City against Regex"),
                                            help=_(
                                                "The city name from the response will be checked against "
                                                "the regular expression specified here"
                                            ),
                                        ),
                                    ),
                                ],
                            ),
                        ),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupIntegrateOtherServices,
        name="active_checks:uniserv",
        valuespec=_valuespec_active_checks_uniserv,
    )
)


def _ip_address_family_element():
    return (
        "address_family",
        DropdownChoice(
            title=_("IP address family"),
            choices=[
                (None, _("Primary address family")),
                ("ipv4", _("Enforce IPv4")),
                ("ipv6", _("Enforce IPv6")),
            ],
            default_value=None,
        ),
    )


def _transform_add_address_family(v):
    v.setdefault("address_family", None)
    return v


def _active_checks_http_proxyspec():
    return Dictionary(
        title=_("Use proxy"),
        elements=[
            ("address", Hostname(title=_("Proxy server address"))),
            ("port", _active_checks_http_portspec(80)),
            (
                "auth",
                Tuple(
                    title=_("Proxy basic authorization"),
                    elements=[
                        TextInput(title=_("Username"), size=12, allow_empty=False),
                        IndividualOrStoredPassword(
                            title=_("Password"),
                        ),
                    ],
                ),
            ),
        ],
        required_keys=["address"],
    )


def _active_checks_http_hostspec():
    return Dictionary(
        title=_("Host settings"),
        help=_(
            "Usually Checkmk will nail this check to the primary IP address of the host"
            " it is attached to. It will use the corresponding IP version (IPv4/IPv6) and"
            " default port (80/443). With this option you can override either of these"
            " parameters. By default no virtual host is set and HTTP/1.0 will be used."
            " In some setups however, you may want to distiguish the contacted server"
            " address from your virtual host name (e.g. if the virtual host name is"
            " not resolvable by DNS). In this case the HTTP Host header will be set and "
            "HTTP/1.1 is used."
        ),
        elements=[
            ("address", Hostname(title=_("Hosts name / IP address"))),
            ("port", _active_checks_http_portspec(443)),
            _ip_address_family_element(),
            (
                "virthost",
                Hostname(
                    title=_("Virtual host"),
                    help=_(
                        "Set this in order to specify the name of the"
                        " virtual host for the query."
                    ),
                ),
            ),
        ],
    )


def _active_checks_http_validate_all(value, varprefix):
    _name, mode = value["mode"]
    if "proxy" in value and "virthost" in mode:
        msg = _("Unfortunately, using a proxy and a virtual host is not supported (try '%s').") % _(
            "Host settings"
        )
        raise MKUserError(varprefix, msg)


def _active_checks_http_portspec(default):
    return Integer(title=_("TCP Port"), minvalue=1, maxvalue=65535, default_value=default)


def _active_checks_http_transform_check_http(params):
    if isinstance(params, dict):
        return params
    name, mode = copy.deepcopy(params)
    # The "verbose" option was part configurable since 1.5.0i1 and has been dropped
    # with 1.5.0p12 (see #5224 and #7079 for additional information).
    mode.pop("verbose", None)
    mode_name = "cert" if "cert_days" in mode else "url"
    transformed = {"name": name, "mode": (mode_name, mode)}
    # The proxy option has been isolated in version 1.6.0i1
    proxy_address = mode.pop("proxy", None)
    if proxy_address:
        proxy = transformed.setdefault("proxy", {"address": proxy_address})
        # ':' outside a IPv6 address indicates port
        if ":" in proxy_address.split("]")[-1]:
            addr, port = proxy_address.rsplit(":", 1)
            try:
                proxy["port"] = int(port)
                proxy["address"] = addr
            except ValueError:
                pass  # leave address as it is
        auth = mode.pop("proxy_auth", None)
        if auth:
            proxy["auth"] = auth
    # The host options have ben isolated in version 1.6.0i1
    host_settings = transformed.setdefault("host", {})
    # URL mode:
    if "virthost" in mode:
        virthost, omit_ip = mode.pop("virthost")
        host_settings["virthost"] = virthost
        if omit_ip or proxy_address:
            host_settings["address"] = virthost
    # CERT mode:
    if "cert_host" in mode:
        host_settings["address"] = mode.pop("cert_host")
    # both modes:
    for key in ("port", "address_family"):
        if key in mode:
            host_settings[key] = mode.pop(key)
    mode.pop("sni", None)
    return transformed


def _validate_active_check_http_name(value, varprefix):
    if value.strip() == "^":
        raise MKUserError(varprefix, _("Please provide a valid name"))


def _valuespec_active_checks_http():
    return Transform(
        Dictionary(
            title=_("Check HTTP service"),
            help=_(
                "Check HTTP/HTTPS service using the plugin <tt>check_http</tt> "
                "from the standard Monitoring Plugins. "
                "This plugin tests the HTTP service on the specified host. "
                "It can test normal (HTTP) and secure (HTTPS) servers, follow "
                "redirects, search for strings and regular expressions, check "
                "connection times, and report on certificate expiration times."
            ),
            elements=[
                (
                    "name",
                    TextInput(
                        title=_("Service name"),
                        help=_(
                            "Will be used in the service description. If the name starts with "
                            "a caret (<tt>^</tt>), the service description will not be prefixed with either "
                            "<tt>HTTP</tt> or <tt>HTTPS</tt>."
                        ),
                        allow_empty=False,
                        size=45,
                        validate=_validate_active_check_http_name,
                    ),
                ),
                ("host", _active_checks_http_hostspec()),
                ("proxy", _active_checks_http_proxyspec()),
                (
                    "mode",
                    CascadingDropdown(
                        title=_("Mode of the Check"),
                        help=_("Perform a check of the URL or the certificate expiration."),
                        choices=[
                            (
                                "url",
                                _("Check the URL"),
                                Dictionary(
                                    title=_("URL Checking"),
                                    elements=[
                                        (
                                            "uri",
                                            Hostname(
                                                title=_("URI to fetch (default is <tt>/</tt>)"),
                                                help=_(
                                                    "The URI of the request. This should start with"
                                                    " '/' and not include the domain"
                                                    " (e.g. '/index.html')."
                                                ),
                                                default_value="/",
                                            ),
                                        ),
                                        (
                                            "ssl",
                                            Transform(
                                                DropdownChoice(
                                                    title=_("Use SSL/HTTPS for the connection"),
                                                    choices=[
                                                        (
                                                            "auto",
                                                            _("Use SSL with auto negotiation"),
                                                        ),
                                                        ("1.2", _("Use SSL, enforce TLSv1.2")),
                                                        ("1.1", _("Use SSL, enforce TLSv1.1")),
                                                        ("1", _("Use SSL, enforce TLSv1")),
                                                        ("2", _("Use SSL, enforce SSLv2")),
                                                        ("3", _("Use SSL, enforce SSLv3")),
                                                    ],
                                                    default_value="auto",
                                                ),
                                                forth=lambda x: x is True and "auto" or x,
                                            ),
                                        ),
                                        (
                                            "response_time",
                                            Tuple(
                                                title=_("Expected response time"),
                                                elements=[
                                                    Float(
                                                        title=_("Warning if above"),
                                                        unit="ms",
                                                        default_value=100.0,
                                                    ),
                                                    Float(
                                                        title=_("Critical if above"),
                                                        unit="ms",
                                                        default_value=200.0,
                                                    ),
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
                                            "user_agent",
                                            TextInput(
                                                title=_("User Agent"),
                                                help=_(
                                                    'String to be sent in http header as "User Agent"'
                                                ),
                                                allow_empty=False,
                                            ),
                                        ),
                                        (
                                            "add_headers",
                                            ListOfStrings(
                                                title=_("Additional header lines"),
                                                orientation="vertical",
                                                valuespec=TextInput(size=40),
                                            ),
                                        ),
                                        (
                                            "auth",
                                            Tuple(
                                                title=_("Authorization"),
                                                help=_("Credentials for HTTP Basic Authentication"),
                                                elements=[
                                                    TextInput(
                                                        title=_("Username"),
                                                        size=12,
                                                        allow_empty=False,
                                                    ),
                                                    IndividualOrStoredPassword(
                                                        title=_("Password"),
                                                    ),
                                                ],
                                            ),
                                        ),
                                        (
                                            "onredirect",
                                            DropdownChoice(
                                                title=_("How to handle redirect"),
                                                choices=[
                                                    ("ok", _("Make check OK")),
                                                    ("warning", _("Make check WARNING")),
                                                    ("critical", _("Make check CRITICAL")),
                                                    ("follow", _("Follow the redirection")),
                                                    (
                                                        "sticky",
                                                        _("Follow, but stay to same IP address"),
                                                    ),
                                                    (
                                                        "stickyport",
                                                        _(
                                                            "Follow, but stay to same IP-address and port"
                                                        ),
                                                    ),
                                                ],
                                                default_value="follow",
                                            ),
                                        ),
                                        (
                                            "expect_response_header",
                                            TextInput(
                                                title=_("String to expect in response headers"),
                                            ),
                                        ),
                                        (
                                            "expect_response",
                                            ListOfStrings(
                                                title=_("Strings to expect in server response"),
                                                help=_(
                                                    "At least one of these strings is expected in "
                                                    "the first (status) line of the server response "
                                                    "(default: <tt>HTTP/1.</tt>). If specified skips "
                                                    "all other status line logic (ex: 3xx, 4xx, 5xx "
                                                    "processing)"
                                                ),
                                            ),
                                        ),
                                        (
                                            "expect_string",
                                            TextInput(
                                                title=_("Fixed string to expect in the content"),
                                                allow_empty=False,
                                            ),
                                        ),
                                        (
                                            "expect_regex",
                                            Transform(
                                                Tuple(
                                                    orientation="vertical",
                                                    show_titles=False,
                                                    elements=[
                                                        RegExp(
                                                            label=_("Regular expression: "),
                                                            mode=RegExp.infix,
                                                            maxlen=1023,
                                                        ),
                                                        Checkbox(label=_("Case insensitive")),
                                                        Checkbox(
                                                            label=_(
                                                                "return CRITICAL if found, OK if not"
                                                            )
                                                        ),
                                                        Checkbox(
                                                            label=_("Multiline string matching")
                                                        ),
                                                    ],
                                                ),
                                                forth=lambda x: len(x) == 3
                                                and tuple(list(x) + [False])
                                                or x,
                                                title=_("Regular expression to expect in content"),
                                            ),
                                        ),
                                        (
                                            "post_data",
                                            Tuple(
                                                title=_("Send HTTP POST data"),
                                                elements=[
                                                    TextInput(
                                                        title=_("HTTP POST data"),
                                                        help=_(
                                                            "Data to send via HTTP POST method. "
                                                            "Please make sure, that the data is URL-encoded."
                                                        ),
                                                        size=40,
                                                    ),
                                                    TextInput(
                                                        title=_("Content-Type"),
                                                        default_value="text/html",
                                                    ),
                                                ],
                                            ),
                                        ),
                                        (
                                            "method",
                                            DropdownChoice(
                                                title=_("HTTP Method"),
                                                default_value="GET",
                                                choices=[
                                                    ("GET", "GET"),
                                                    ("POST", "POST"),
                                                    ("OPTIONS", "OPTIONS"),
                                                    ("TRACE", "TRACE"),
                                                    ("PUT", "PUT"),
                                                    ("DELETE", "DELETE"),
                                                    ("HEAD", "HEAD"),
                                                    ("CONNECT", "CONNECT"),
                                                    ("PROPFIND", "PROPFIND"),
                                                ],
                                            ),
                                        ),
                                        (
                                            "no_body",
                                            FixedValue(
                                                value=True,
                                                title=_("Don't wait for document body"),
                                                help=_(
                                                    "Note: this still does an HTTP GET or POST, not a HEAD."
                                                ),
                                                totext=_("don't wait for body"),
                                            ),
                                        ),
                                        (
                                            "page_size",
                                            Tuple(
                                                title=_("Page size to expect"),
                                                elements=[
                                                    Integer(title=_("Minimum"), unit=_("Bytes")),
                                                    Integer(title=_("Maximum"), unit=_("Bytes")),
                                                ],
                                            ),
                                        ),
                                        (
                                            "max_age",
                                            Age(
                                                title=_("Maximum age"),
                                                help=_(
                                                    "Warn, if the age of the page is older than this"
                                                ),
                                                default_value=3600 * 24,
                                            ),
                                        ),
                                        (
                                            "urlize",
                                            FixedValue(
                                                value=True,
                                                title=_("Clickable URLs"),
                                                totext=_("Format check output as hyperlink"),
                                                help=_(
                                                    "With this option the check produces an output that is a valid hyperlink "
                                                    "to the checked URL and this clickable."
                                                ),
                                            ),
                                        ),
                                        (
                                            "extended_perfdata",
                                            FixedValue(
                                                value=True,
                                                totext=_("Extended perfdata"),
                                                title=_("Record additional performance data"),
                                                help=_(
                                                    "This option makes the HTTP check produce more detailed performance data values "
                                                    "like the connect time, header time, time till first byte received and the "
                                                    "transfer time."
                                                ),
                                            ),
                                        ),
                                    ],
                                ),
                            ),
                            (
                                "cert",
                                _("Check SSL Certificate Age"),
                                Dictionary(
                                    title=_("Certificate Checking"),
                                    help=_(
                                        "Port defaults to 443. In this mode the URL"
                                        " is not checked."
                                    ),
                                    elements=[
                                        (
                                            "cert_days",
                                            Transform(
                                                Tuple(
                                                    title=_("Age"),
                                                    help=_(
                                                        "Minimum number of days a certificate"
                                                        " has to be valid."
                                                    ),
                                                    elements=[
                                                        Integer(
                                                            title=_("Warning at or below"),
                                                            minvalue=0,
                                                            unit=_("days"),
                                                        ),
                                                        Integer(
                                                            title=_("Critical at or below"),
                                                            minvalue=0,
                                                            unit=_("days"),
                                                        ),
                                                    ],
                                                ),
                                                forth=transform_cert_days,
                                            ),
                                        ),
                                    ],
                                    required_keys=["cert_days"],
                                ),
                            ),
                        ],
                    ),
                ),
                (
                    "disable_sni",
                    FixedValue(
                        value=True,
                        totext="",
                        title=_("Advanced: Disable SSL/TLS hostname extension support (SNI)"),
                        help=_(
                            "In earlier versions of Check_MK users had to enable SNI explicitly."
                            " We now assume users allways want SNI support. If you don't, you"
                            " can disable it with this option."
                        ),
                    ),
                ),
            ],
            required_keys=["name", "host", "mode"],
            validate=_active_checks_http_validate_all,
        ),
        forth=_active_checks_http_transform_check_http,
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupActiveChecks,
        match_type="all",
        name="active_checks:http",
        valuespec=_valuespec_active_checks_http,
    )
)


def _valuespec_active_checks_ldap():
    return Tuple(
        title=_("Check LDAP service access"),
        help=_(
            "This check uses <tt>check_ldap</tt> from the standard "
            "Nagios plugins in order to try the response of an LDAP "
            "server."
        ),
        elements=[
            TextInput(
                title=_("Name"),
                help=_(
                    "The service description will be <b>LDAP</b> plus this name. If the name starts with "
                    "a caret (<tt>^</tt>), the service description will not be prefixed with <tt>LDAP</tt>."
                ),
                allow_empty=False,
            ),
            TextInput(
                title=_("Base DN"),
                help=_("LDAP base, e.g. ou=Development, o=tribe29 GmbH, c=de"),
                allow_empty=False,
                size=60,
            ),
            Dictionary(
                title=_("Optional parameters"),
                elements=[
                    (
                        "attribute",
                        TextInput(
                            title=_("Attribute to search"),
                            help=_(
                                "LDAP attribute to search, "
                                "The default is <tt>(objectclass=*)</tt>."
                            ),
                            size=40,
                            allow_empty=False,
                            default_value="(objectclass=*)",
                        ),
                    ),
                    (
                        "authentication",
                        Tuple(
                            title=_("Authentication"),
                            elements=[
                                TextInput(
                                    title=_("Bind DN"),
                                    help=_("Distinguished name for binding"),
                                    allow_empty=False,
                                    size=60,
                                ),
                                IndividualOrStoredPassword(
                                    title=_("Password"),
                                    help=_(
                                        "Password for binding, if your server requires an authentication"
                                    ),
                                    allow_empty=False,
                                    size=20,
                                ),
                            ],
                        ),
                    ),
                    (
                        "port",
                        Integer(
                            title=_("TCP Port"),
                            help=_(
                                "Default is 389 for normal connections and 636 for SSL connections."
                            ),
                            minvalue=1,
                            maxvalue=65535,
                            default_value=389,
                        ),
                    ),
                    (
                        "ssl",
                        FixedValue(
                            value=True,
                            totext=_("Use SSL"),
                            title=_("Use LDAPS (SSL)"),
                            help=_(
                                "Use LDAPS (LDAP SSLv2 method). This sets the default port number to 636"
                            ),
                        ),
                    ),
                    (
                        "hostname",
                        TextInput(
                            title=_("Alternative Hostname"),
                            help=_(
                                "Use a alternative field as Hostname in case of SSL Certificate Problems (eg. the Hostalias )"
                            ),
                            size=40,
                            allow_empty=False,
                            default_value="$HOSTALIAS$",
                        ),
                    ),
                    (
                        "version",
                        DropdownChoice(
                            title=_("LDAP Version"),
                            help=_("The default is to use version 2"),
                            choices=[
                                ("v2", _("Version 2")),
                                ("v3", _("Version 3")),
                                ("v3tls", _("Version 3 and TLS")),
                            ],
                            default_value="v2",
                        ),
                    ),
                    (
                        "response_time",
                        Tuple(
                            title=_("Expected response time"),
                            elements=[
                                Float(title=_("Warning if above"), unit="ms", default_value=1000.0),
                                Float(
                                    title=_("Critical if above"), unit="ms", default_value=2000.0
                                ),
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
                ],
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupActiveChecks,
        match_type="all",
        name="active_checks:ldap",
        valuespec=_valuespec_active_checks_ldap,
    )
)


def _active_checks_smtp_transform_smtp_address_family(val):
    if "ip_version" in val:
        val["address_family"] = val.pop("ip_version")
    return val


def _valuespec_active_checks_smtp():
    return Tuple(
        title=_("Check SMTP service access"),
        help=_(
            "This check uses <tt>check_smtp</tt> from the standard "
            "Nagios plugins in order to try the response of an SMTP "
            "server."
        ),
        elements=[
            TextInput(
                title=_("Name"),
                help=_(
                    "The service description will be <b>SMTP</b> plus this name. If the name starts with "
                    "a caret (<tt>^</tt>), the service description will not be prefixed with <tt>SMTP</tt>."
                ),
                allow_empty=False,
            ),
            Transform(
                Dictionary(
                    title=_("Optional parameters"),
                    elements=[
                        (
                            "hostname",
                            TextInput(
                                title=_("DNS Hostname or IP address"),
                                allow_empty=False,
                                help=_(
                                    "You can specify a hostname or IP address different from the IP address "
                                    "of the host as configured in your host properties."
                                ),
                            ),
                        ),
                        (
                            "port",
                            Transform(
                                Integer(
                                    title=_("TCP Port to connect to"),
                                    help=_(
                                        "The TCP Port the SMTP server is listening on. "
                                        "The default is <tt>25</tt>."
                                    ),
                                    size=5,
                                    minvalue=1,
                                    maxvalue=65535,
                                    default_value=25,
                                ),
                                forth=int,
                            ),
                        ),
                        _ip_address_family_element(),
                        (
                            "expect",
                            TextInput(
                                title=_("Expected String"),
                                help=_(
                                    "String to expect in first line of server response. "
                                    "The default is <tt>220</tt>."
                                ),
                                size=8,
                                allow_empty=False,
                                default_value="220",
                            ),
                        ),
                        (
                            "commands",
                            ListOfStrings(
                                title=_("SMTP Commands"),
                                help=_("SMTP commands to execute."),
                            ),
                        ),
                        (
                            "command_responses",
                            ListOfStrings(
                                title=_("SMTP Responses"),
                                help=_("Expected responses to the given SMTP commands."),
                            ),
                        ),
                        (
                            "from",
                            TextInput(
                                title=_("FROM-Address"),
                                help=_(
                                    "FROM-address to include in MAIL command, required by Exchange 2000"
                                ),
                                size=20,
                                allow_empty=True,
                                default_value="",
                            ),
                        ),
                        (
                            "fqdn",
                            TextInput(
                                title=_("FQDN"),
                                help=_("FQDN used for HELO"),
                                size=20,
                                allow_empty=True,
                                default_value="",
                            ),
                        ),
                        (
                            "cert_days",
                            Transform(
                                Tuple(
                                    title=_("Minimum Certificate Age"),
                                    help=_("Minimum number of days a certificate has to be valid"),
                                    elements=[
                                        Integer(
                                            title=_("Warning at or below"),
                                            minvalue=0,
                                            unit=_("days"),
                                        ),
                                        Integer(
                                            title=_("Critical at or below"),
                                            minvalue=0,
                                            unit=_("days"),
                                        ),
                                    ],
                                ),
                                forth=transform_cert_days,
                            ),
                        ),
                        (
                            "starttls",
                            FixedValue(
                                True,
                                totext=_("STARTTLS enabled."),
                                title=_("Use STARTTLS for the connection."),
                            ),
                        ),
                        (
                            "auth",
                            Tuple(
                                title=_("Enable SMTP AUTH (LOGIN)"),
                                help=_(
                                    "SMTP AUTH type to check (default none, only LOGIN supported)"
                                ),
                                elements=[
                                    TextInput(
                                        title=_("Username"),
                                        size=12,
                                        allow_empty=False,
                                    ),
                                    IndividualOrStoredPassword(
                                        title=_("Password"),
                                        size=12,
                                        allow_empty=False,
                                    ),
                                ],
                            ),
                        ),
                        (
                            "response_time",
                            Tuple(
                                title=_("Expected response time"),
                                elements=[
                                    Float(
                                        title=_("Warning if above"), unit=_("sec"), allow_int=True
                                    ),
                                    Float(
                                        title=_("Critical if above"), unit=_("sec"), allow_int=True
                                    ),
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
                    ],
                ),
                forth=_active_checks_smtp_transform_smtp_address_family,
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupActiveChecks,
        match_type="all",
        name="active_checks:smtp",
        valuespec=_valuespec_active_checks_smtp,
    )
)


def _valuespec_active_checks_disk_smb():
    return Dictionary(
        title=_("Check SMB share access"),
        help=_(
            "This ruleset helps you to configure the classical Nagios "
            "plugin <tt>check_disk_smb</tt> that checks the access to "
            "filesystem shares that are exported via SMB/CIFS."
        ),
        elements=[
            (
                "share",
                TextInput(
                    title=_("SMB share to check"),
                    help=_(
                        "Enter the plain name of the share only, e. g. <tt>iso</tt>, <b>not</b> "
                        "the full UNC like <tt>\\\\servername\\iso</tt>"
                    ),
                    size=32,
                    allow_empty=False,
                ),
            ),
            (
                "workgroup",
                TextInput(
                    title=_("Workgroup"),
                    help=_("Workgroup or domain used (defaults to <tt>WORKGROUP</tt>)"),
                    size=32,
                    allow_empty=False,
                ),
            ),
            (
                "host",
                TextInput(
                    title=_("NetBIOS name of the server"),
                    help=_("If omitted then the IP address is being used."),
                    size=32,
                    allow_empty=False,
                ),
            ),
            (
                "port",
                Integer(
                    title=_("TCP Port"),
                    help=_("TCP port number to connect to. Usually either 139 or 445."),
                    default_value=445,
                    minvalue=1,
                    maxvalue=65535,
                ),
            ),
            (
                "levels",
                Tuple(
                    title=_("Levels for used disk space"),
                    elements=[
                        Percentage(title=_("Warning if above"), default_value=85, allow_int=True),
                        Percentage(title=_("Critical if above"), default_value=95, allow_int=True),
                    ],
                ),
            ),
            (
                "auth",
                Tuple(
                    title=_("Authorization"),
                    elements=[
                        TextInput(title=_("Username"), allow_empty=False, size=24),
                        Password(title=_("Password"), allow_empty=False, size=12),
                    ],
                ),
            ),
        ],
        required_keys=["share", "levels"],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupActiveChecks,
        match_type="all",
        name="active_checks:disk_smb",
        valuespec=_valuespec_active_checks_disk_smb,
    )
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
                    title=_("Performance data"),
                    value=True,
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


def _active_checks_bi_aggr_transform_from_disk(value):
    if isinstance(value, dict):
        return value
    new_value = {}
    new_value["base_url"] = value[0]
    new_value["aggregation_name"] = value[1]
    new_value["optional"] = value[4]
    new_value["credentials"] = ("configured", (value[2], value[3]))
    return new_value


def _valuespec_active_checks_bi_aggr():
    return Transform(
        Dictionary(
            title=_("Check State of BI Aggregation"),
            help=_(
                "Connect to the local or a remote monitoring host, which uses Check_MK BI to aggregate "
                "several states to a single BI aggregation, which you want to show up as a single "
                "service."
            ),
            elements=[
                (
                    "base_url",
                    TextInput(
                        title=_("Base URL (OMD Site)"),
                        help=_(
                            "The base URL to the monitoring instance. For example <tt>http://mycheckmk01/mysite</tt>. "
                            "You can use macros like <tt>$HOSTADDRESS$</tt> and <tt>$HOSTNAME$</tt> within this URL to "
                            "make them be replaced by the hosts values."
                        ),
                        size=60,
                        allow_empty=False,
                    ),
                ),
                (
                    "aggregation_name",
                    TextInput(
                        title=_("Aggregation Name"),
                        help=_(
                            "The name of the aggregation to fetch. It will be added to the service description. You can "
                            "use macros like <tt>$HOSTADDRESS$</tt> and <tt>$HOSTNAME$</tt> within this parameter to "
                            "make them be replaced by the hosts values. The aggregation name is the title in the "
                            "top-level-rule of your BI pack."
                        ),
                        allow_empty=False,
                    ),
                ),
                (
                    "credentials",
                    CascadingDropdown(
                        choices=[
                            ("automation", _("Use the credentials of the 'automation' user")),
                            (
                                "configured",
                                _("Use the following credentials"),
                                Tuple(
                                    elements=[
                                        TextInput(
                                            title=_("Automation Username"),
                                            allow_empty=True,
                                            help=_(
                                                "The name of the automation account to use for fetching the BI aggregation via HTTP. Note: You may "
                                                "also set credentials of a standard user account, though it is disadvised. "
                                                "Using the credentials of a standard user also requires a valid authentication method set in the "
                                                "optional parameters."
                                            ),
                                        ),
                                        IndividualOrStoredPassword(
                                            title=_("Automation Secret"),
                                            help=_(
                                                "Valid automation secret for the automation user"
                                            ),
                                            allow_empty=False,
                                        ),
                                    ]
                                ),
                            ),
                        ],
                        help=_(
                            "Here you can configured the credentials to be used. Keep in mind that the <tt>automation</tt> user need "
                            "to exist if you choose this option"
                        ),
                        title=_("Login credentials"),
                        default_value="automation",
                    ),
                ),
                (
                    "optional",
                    Dictionary(
                        title=_("Optional parameters"),
                        elements=[
                            (
                                "auth_mode",
                                DropdownChoice(
                                    title=_("Authentication Mode"),
                                    default_value="cookie",
                                    choices=[
                                        ("cookie", _("Form (Cookie) based")),
                                        ("basic", _("HTTP Basic")),
                                        ("digest", _("HTTP Digest")),
                                        ("kerberos", _("Kerberos")),
                                    ],
                                ),
                            ),
                            (
                                "timeout",
                                Integer(
                                    title=_("Seconds before connection times out"),
                                    unit=_("sec"),
                                    default_value=60,
                                ),
                            ),
                            (
                                "in_downtime",
                                DropdownChoice(
                                    title=_("State, if BI aggregate is in scheduled downtime"),
                                    choices=[
                                        (None, _("Use normal state, ignore downtime")),
                                        ("ok", _("Force to be OK")),
                                        ("warn", _("Force to be WARN, if aggregate is not OK")),
                                    ],
                                ),
                            ),
                            (
                                "acknowledged",
                                DropdownChoice(
                                    title=_("State, if BI aggregate is acknowledged"),
                                    choices=[
                                        (None, _("Use normal state, ignore acknowledgement")),
                                        ("ok", _("Force to be OK")),
                                        ("warn", _("Force to be WARN, if aggregate is not OK")),
                                    ],
                                ),
                            ),
                            (
                                "track_downtimes",
                                Checkbox(
                                    title=_("Track downtimes"),
                                    label=_("Automatically track downtimes of aggregation"),
                                    help=_(
                                        "If this is active, the check will automatically go into downtime "
                                        "whenever the aggregation does. This downtime is also cleaned up "
                                        "automatically when the aggregation leaves downtime. "
                                        "Downtimes you set manually for this check are unaffected."
                                    ),
                                ),
                            ),
                        ],
                    ),
                ),
            ],
            optional_keys=False,
        ),
        forth=_active_checks_bi_aggr_transform_from_disk,
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupIntegrateOtherServices,
        match_type="all",
        name="active_checks:bi_aggr",
        valuespec=_valuespec_active_checks_bi_aggr,
    )
)


def _valuespec_active_checks_form_submit():
    return Tuple(
        title=_("Check HTML Form Submit"),
        help=_(
            "Check submission of HTML forms via HTTP/HTTPS using the plugin <tt>check_form_submit</tt> "
            "provided with Check_MK. This plugin provides more functionality than <tt>check_http</tt>, "
            "as it automatically follows HTTP redirect, accepts and uses cookies, parses forms "
            "from the requested pages, changes vars and submits them to check the response "
            "afterwards."
        ),
        elements=[
            TextInput(
                title=_("Name"),
                help=_("The name will be used in the service description"),
                allow_empty=False,
            ),
            Dictionary(
                title=_("Check the URL"),
                elements=[
                    (
                        "hosts",
                        ListOfStrings(
                            title=_("Check specific host(s)"),
                            help=_(
                                "By default, if you do not specify any host addresses here, "
                                "the host address of the host this service is assigned to will "
                                "be used. But by specifying one or several host addresses here, "
                                "it is possible to let the check monitor one or multiple hosts."
                            ),
                        ),
                    ),
                    (
                        "virthost",
                        TextInput(
                            title=_("Virtual host"),
                            help=_(
                                "Set this in order to specify the name of the "
                                "virtual host for the query (using HTTP/1.1). When you "
                                "leave this empty, then the IP address of the host "
                                "will be used instead."
                            ),
                            allow_empty=False,
                        ),
                    ),
                    (
                        "uri",
                        TextInput(
                            title=_("URI to fetch (default is <tt>/</tt>)"),
                            allow_empty=False,
                            default_value="/",
                            regex="^/.*",
                        ),
                    ),
                    (
                        "port",
                        Integer(
                            title=_("TCP Port"),
                            minvalue=1,
                            maxvalue=65535,
                            default_value=80,
                        ),
                    ),
                    (
                        "ssl",
                        FixedValue(
                            value=True,
                            totext=_("use SSL/HTTPS"),
                            title=_("Use SSL/HTTPS for the connection."),
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
                        "expect_regex",
                        RegExp(
                            title=_("Regular expression to expect in content"),
                            mode=RegExp.infix,
                        ),
                    ),
                    (
                        "form_name",
                        TextInput(
                            title=_("Name of the form to populate and submit"),
                            help=_(
                                "If there is only one form element on the requested page, you "
                                "do not need to provide the name of that form here. But if you "
                                "have several forms on that page, you need to provide the name "
                                "of the form here, to enable the check to identify the correct "
                                "form element."
                            ),
                            allow_empty=True,
                        ),
                    ),
                    (
                        "query",
                        TextInput(
                            title=_("Send HTTP POST data"),
                            help=_(
                                "Data to send via HTTP POST method. Please make sure, that the data "
                                'is URL-encoded (for example "key1=val1&key2=val2").'
                            ),
                            size=40,
                        ),
                    ),
                    (
                        "num_succeeded",
                        Tuple(
                            title=_("Multiple Hosts: Number of successful results"),
                            elements=[
                                Integer(title=_("Warning if equal or below")),
                                Integer(title=_("Critical if equal or below")),
                            ],
                        ),
                    ),
                ],
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupActiveChecks,
        match_type="all",
        name="active_checks:form_submit",
        valuespec=_valuespec_active_checks_form_submit,
    )
)


def _valuespec_active_checks_notify_count():
    return Tuple(
        title=_("Check notification number per contact"),
        help=_(
            "Check the number of sent notifications per contact using the plugin <tt>check_notify_count</tt> "
            "provided with Check_MK. This plugin counts the total number of notifications sent by the local "
            "monitoring core and creates graphs for each individual contact. You can configure thresholds "
            "on the number of notifications per contact in a defined time interval. "
            "This plugin queries livestatus to extract the notification related log entries from the "
            "log file of your monitoring core."
        ),
        elements=[
            TextInput(
                title=_("Service Description"),
                help=_("The name that will be used in the service description"),
                allow_empty=False,
            ),
            Integer(
                title=_("Interval to monitor"),
                label=_("notifications within last"),
                unit=_("minutes"),
                minvalue=1,
                default_value=60,
            ),
            Dictionary(
                title=_("Optional parameters"),
                elements=[
                    (
                        "num_per_contact",
                        Tuple(
                            title=_("Thresholds for Notifications per Contact"),
                            elements=[
                                Integer(title=_("Warning if above"), default_value=20),
                                Integer(title=_("Critical if above"), default_value=50),
                            ],
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
        name="active_checks:notify_count",
        valuespec=_valuespec_active_checks_notify_count,
    )
)


def _valuespec_active_checks_traceroute():
    return Transform(
        Dictionary(
            title=_("Check current routing"),
            help=_(
                "This active check uses <tt>traceroute</tt> in order to determine the current "
                "routing from the monitoring host to the target host. You can specify any number "
                "of missing or expected routes in order to detect e.g. an (unintended) failover "
                "to a secondary route."
            ),
            elements=[
                (
                    "dns",
                    Checkbox(
                        title=_("Name resolution"),
                        label=_("Use DNS to convert IP addresses into hostnames"),
                        help=_(
                            "If you use this option, then <tt>traceroute</tt> is <b>not</b> being "
                            "called with the option <tt>-n</tt>. That means that all IP addresses "
                            "are tried to be converted into names. This usually adds additional "
                            "execution time. Also DNS resolution might fail for some addresses."
                        ),
                    ),
                ),
                _ip_address_family_element(),
                (
                    "routers",
                    ListOf(
                        Tuple(
                            elements=[
                                TextInput(
                                    title=_("Router (FQDN, IP-Address)"),
                                    allow_empty=False,
                                ),
                                DropdownChoice(
                                    title=_("How"),
                                    choices=[
                                        ("W", _("WARN - if this router is not being used")),
                                        ("C", _("CRIT - if this router is not being used")),
                                        ("w", _("WARN - if this router is being used")),
                                        ("c", _("CRIT - if this router is being used")),
                                    ],
                                ),
                            ]
                        ),
                        title=_("Router that must or must not be used"),
                        add_label=_("Add Condition"),
                    ),
                ),
                (
                    "method",
                    DropdownChoice(
                        title=_("Method of probing"),
                        choices=[
                            (None, _("UDP (default behaviour of traceroute)")),
                            ("icmp", _("ICMP Echo Request")),
                            ("tcp", _("TCP SYN")),
                        ],
                    ),
                ),
            ],
            optional_keys=False,
        ),
        forth=_transform_add_address_family,
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupActiveChecks,
        match_type="all",
        name="active_checks:traceroute",
        valuespec=_valuespec_active_checks_traceroute,
    )
)


def _valuespec_active_checks_mail_loop():
    return Dictionary(
        title=_("Check Email Delivery"),
        help=_(
            "This active check sends out special E-Mails to a defined mail address using "
            "the SMTP protocol and then tries to receive these mails back by querying the "
            "inbox of a IMAP or POP3 mailbox. With this check you can verify that your whole "
            "mail delivery progress is working."
        ),
        optional_keys=[
            "subject",
            "smtp_server",
            "smtp_tls",
            "smtp_port",
            "smtp_auth",
            "imap_tls",
            "connect_timeout",
            "delete_messages",
            "duration",
        ],
        elements=[
            (
                "item",
                TextInput(
                    title=_("Name"),
                    help=_("The service description will be <b>Mail Loop</b> plus this name"),
                    allow_empty=False,
                ),
            ),
            (
                "subject",
                TextInput(
                    title=_("Subject"),
                    allow_empty=False,
                    help=_(
                        "Here you can specify the subject text "
                        "instead of default text 'Check_MK-Mail-Loop'."
                    ),
                ),
            ),
            (
                "smtp_server",
                TextInput(
                    title=_("SMTP Server"),
                    allow_empty=False,
                    help=_(
                        "You can specify a hostname or IP address different from the IP address "
                        "of the host this check will be assigned to."
                    ),
                ),
            ),
            (
                "smtp_tls",
                FixedValue(
                    True,
                    title=_("Use TLS over SMTP"),
                    totext=_("Encrypt SMTP communication using TLS"),
                ),
            ),
            (
                "imap_tls",
                FixedValue(
                    True,
                    title=_("Use TLS for IMAP authentification"),
                    totext=_("IMAP authentification uses TLS"),
                ),
            ),
            (
                "smtp_port",
                Integer(
                    title=_("SMTP TCP Port to connect to"),
                    help=_(
                        "The TCP Port the SMTP server is listening on. Defaulting to <tt>25</tt>."
                    ),
                    default_value=25,
                ),
            ),
            (
                "smtp_auth",
                Tuple(
                    title=_("SMTP Authentication"),
                    elements=[
                        TextInput(title=_("Username"), allow_empty=False, size=24),
                        IndividualOrStoredPassword(title=_("Password"), allow_empty=False, size=12),
                    ],
                ),
            ),
        ]
        + _mail_receiving_params()
        + [
            (
                "mail_from",
                EmailAddress(
                    title=_("From: email address"),
                ),
            ),
            (
                "mail_to",
                EmailAddress(
                    title=_("Destination email address"),
                ),
            ),
            (
                "connect_timeout",
                Integer(
                    title=_("Connect Timeout"),
                    minvalue=1,
                    default_value=10,
                    unit=_("sec"),
                ),
            ),
            (
                "duration",
                Tuple(
                    title=_("Loop duration"),
                    elements=[
                        Age(title=_("Warning at")),
                        Age(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "delete_messages",
                FixedValue(
                    True,
                    title=_("Delete processed messages"),
                    totext=_("Delete all processed message belonging to this check"),
                    help=_(
                        "Delete all messages identified as being related to this "
                        "check. This is disabled by default, which will make "
                        "your mailbox grow when you not clean it up on your own."
                    ),
                ),
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupActiveChecks,
        match_type="all",
        name="active_checks:mail_loop",
        valuespec=_valuespec_active_checks_mail_loop,
    )
)


def _valuespec_active_checks_mail():
    return Dictionary(
        title=_("Check Email"),
        help=_(
            "The basic function of this check is to log in into an IMAP or POP3 mailbox to "
            "monitor whether or not the login is possible. A extended feature is, that the "
            "check can fetch all (or just some) from the mailbox and forward them as events "
            "to the Event Console."
        ),
        required_keys=["service_description", "fetch"],
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
                    default_value="Email",
                ),
            )
        ]
        + _mail_receiving_params()
        + [
            (
                "connect_timeout",
                Integer(
                    title=_("Connect Timeout"),
                    minvalue=1,
                    default_value=10,
                    unit=_("sec"),
                ),
            ),
            (
                "forward",
                Dictionary(
                    title=_("Forward mails as events to Event Console"),
                    elements=[
                        (
                            "method",
                            Alternative(
                                title=_("Forwarding Method"),
                                elements=[
                                    Alternative(
                                        title=_("Send events to local event console"),
                                        elements=[
                                            FixedValue(
                                                "",
                                                totext=_("Directly forward to event console"),
                                                title=_(
                                                    "Send events to local event console in same OMD site"
                                                ),
                                            ),
                                            TextInput(
                                                title=_(
                                                    "Send events to local event console into unix socket"
                                                ),
                                                allow_empty=False,
                                            ),
                                            FixedValue(
                                                "spool:",
                                                totext=_("Spool to event console"),
                                                title=_(
                                                    "Spooling: Send events to local event console in same OMD site"
                                                ),
                                            ),
                                            Transform(
                                                TextInput(
                                                    allow_empty=False,
                                                ),
                                                title=_(
                                                    "Spooling: Send events to local event console into given spool directory"
                                                ),
                                                # remove prefix
                                                forth=lambda x: x[6:],
                                                back=lambda x: "spool:" + x,  # add prefix
                                            ),
                                        ],
                                        match=lambda x: x
                                        and (
                                            x == "spool:" and 2 or x.startswith("spool:") and 3 or 1
                                        )
                                        or 0,
                                    ),
                                    Tuple(
                                        title=_("Send events to remote syslog host"),
                                        elements=[
                                            DropdownChoice(
                                                choices=[
                                                    ("udp", _("UDP")),
                                                    ("tcp", _("TCP")),
                                                ],
                                                title=_("Protocol"),
                                            ),
                                            TextInput(
                                                title=_("Address"),
                                                allow_empty=False,
                                            ),
                                            Integer(
                                                title=_("Port"),
                                                default_value=514,
                                                minvalue=1,
                                                maxvalue=65535,
                                                size=6,
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                        ),
                        (
                            "match_subject",
                            RegExp(
                                title=_("Only process mails with matching subject"),
                                help=_(
                                    "Use this option to not process all messages found in the inbox, "
                                    "but only the those whose subject matches the given regular expression."
                                ),
                                mode=RegExp.prefix,
                            ),
                        ),
                        (
                            "facility",
                            DropdownChoice(
                                title=_("Events: Syslog facility"),
                                help=_("Use this syslog facility for all created events"),
                                choices=mkeventd.syslog_facilities,
                                default_value=2,  # mail
                            ),
                        ),
                        (
                            "application",
                            Alternative(
                                title=_("Events: Syslog application"),
                                help=_("Use this syslog application for all created events"),
                                elements=[
                                    FixedValue(
                                        None,
                                        title=_("Use the mail subject"),
                                        totext=_("The mail subject is used as syslog appliaction"),
                                    ),
                                    TextInput(
                                        title=_("Specify the application"),
                                        help=_(
                                            "Use this text as application. You can use macros like <tt>\\1</tt>, <tt>\\2</tt>, ... "
                                            "here when you configured <i>subject matching</i> in this rule with a regular expression "
                                            "that declares match groups (using braces)."
                                        ),
                                        allow_empty=False,
                                    ),
                                ],
                            ),
                        ),
                        (
                            "host",
                            TextInput(
                                title=_("Events: Hostname"),
                                help=_(
                                    "Use this hostname for all created events instead of the name of the mailserver"
                                ),
                            ),
                        ),
                        (
                            "body_limit",
                            Integer(
                                title=_("Limit length of mail body"),
                                help=_(
                                    "When forwarding mails from the mailbox to the event console, the "
                                    "body of the mail is limited to the given number of characters."
                                ),
                                default_value=1000,
                            ),
                        ),
                        (
                            "cleanup",
                            Alternative(
                                title=_("Cleanup messages"),
                                help=_(
                                    "The handled messages (see <i>subject matching</i>) can be cleaned up by either "
                                    "deleting them or moving them to a subfolder. By default nothing is cleaned up."
                                ),
                                elements=[
                                    FixedValue(
                                        True,
                                        title=_("Delete messages"),
                                        totext=_(
                                            "Delete all processed message belonging to this check"
                                        ),
                                    ),
                                    TextInput(
                                        title=_("Move to subfolder"),
                                        help=_(
                                            "Specify the destination path in the format <tt>Path/To/Folder</tt>, for example"
                                            "<tt>INBOX/Processed_Mails</tt>."
                                        ),
                                        allow_empty=False,
                                    ),
                                ],
                            ),
                        ),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupActiveChecks,
        match_type="all",
        name="active_checks:mail",
        valuespec=_valuespec_active_checks_mail,
    )
)


def _valuespec_active_checks_mailboxes():
    return Dictionary(
        title=_("Check IMAP Mailboxes"),
        help=_("This check monitors count and age of mails in mailboxes."),
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
                    default_value="Mailboxes",
                ),
            ),
            ("imap_parameters", _imap_parameters()),
            (
                "connect_timeout",
                Integer(
                    title=_("Connect Timeout"),
                    minvalue=1,
                    default_value=10,
                    unit=_("sec"),
                ),
            ),
            (
                "age",
                Tuple(
                    title=_("Message Age of oldest messages"),
                    elements=[
                        Age(title=_("Warning if older than")),
                        Age(title=_("Critical if older than")),
                    ],
                ),
            ),
            (
                "age_newest",
                Tuple(
                    title=_("Message Age of newest messages"),
                    elements=[
                        Age(title=_("Warning if older than")),
                        Age(title=_("Critical if older than")),
                    ],
                ),
            ),
            (
                "count",
                Tuple(
                    title=_("Message Count"),
                    elements=[Integer(title=_("Warning at")), Integer(title=_("Critical at"))],
                ),
            ),
            (
                "mailboxes",
                ListOfStrings(
                    title=_("Check only the listed mailboxes"),
                    help=_(
                        "By default, all mailboxes are checked with these parameters. "
                        "If you specify mailboxes here, only those are monitored."
                    ),
                ),
            ),
        ],
        required_keys=["service_description", "imap_parameters"],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupActiveChecks,
        match_type="all",
        name="active_checks:mailboxes",
        valuespec=_valuespec_active_checks_mailboxes,
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
                                FixedValue("ipv4", totext="", title=_("IPv4")),
                                FixedValue("ipv6", totext="", title=_("IPv6")),
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
                            True,
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
