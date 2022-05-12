#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy
from typing import Mapping

from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.active_checks.common import (
    RulespecGroupActiveChecks,
    RulespecGroupIntegrateOtherServices,
    transform_cert_days,
)
from cmk.gui.plugins.wato.utils import (
    HostRulespec,
    IndividualOrStoredPassword,
    PasswordFromStore,
    PluginCommandLine,
    rulespec_registry,
)
from cmk.gui.valuespec import (
    Age,
    Alternative,
    CascadingDropdown,
    Checkbox,
    Dictionary,
    DropdownChoice,
    FixedValue,
    Float,
    Integer,
    ListOf,
    ListOfStrings,
    Password,
    Percentage,
    RegExp,
    TextInput,
    Transform,
    Tuple,
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
            ("address", TextInput(title=_("Proxy server address"), size=45)),
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
            ("address", TextInput(title=_("Hostname / IP address"), allow_empty=False, size=45)),
            ("port", _active_checks_http_portspec(443)),
            _ip_address_family_element(),
            (
                "virthost",
                TextInput(
                    title=_("Virtual host"),
                    help=_(
                        "Set this in order to specify the name of the"
                        " virtual host for the query."
                    ),
                    allow_empty=False,
                    size=45,
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
        valuespec=Dictionary(
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
                        validate=_validate_active_check_http_name,
                        size=45,
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
                                            TextInput(
                                                title=_("URI to fetch (default is <tt>/</tt>)"),
                                                help=_(
                                                    "The URI of the request. This should start with"
                                                    " '/' and not include the domain"
                                                    " (e.g. '/index.html')."
                                                ),
                                                allow_empty=False,
                                                default_value="/",
                                                size=45,
                                            ),
                                        ),
                                        (
                                            "ssl",
                                            Transform(
                                                valuespec=DropdownChoice(
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
                                                valuespec=Tuple(
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
                                                valuespec=Tuple(
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
                valuespec=Dictionary(
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
                                valuespec=Integer(
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
                                valuespec=Tuple(
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
                                value=True,
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
        valuespec=Dictionary(
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
    return Transform(
        Tuple(
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
                            "tls_configuration",
                            DropdownChoice(
                                title=_("TLS/HTTPS configuration"),
                                help=_(
                                    "Activate or deactivate TLS for the connection. No certificate validation means that "
                                    "the server certificate will not be validated by the locally available certificate authorities."
                                ),
                                choices=[
                                    (
                                        "no_tls",
                                        _("No TLS"),
                                    ),
                                    (
                                        "tls_standard",
                                        _("TLS"),
                                    ),
                                    (
                                        "tls_no_cert_valid",
                                        _("TLS without certificate validation"),
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
        ),
        forth=_transform_form_submit,
    )


def _transform_form_submit(p: tuple[str, Mapping[str, object]]) -> tuple[str, Mapping[str, object]]:
    service_name, params = p
    if "tls_configuration" in params:
        return p
    if "ssl" not in params:
        return p
    return service_name, {
        **{k: v for k, v in params.items() if k != "ssl"},
        "tls_configuration": "tls_standard",
    }


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
        valuespec=Dictionary(
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
                        valuespec=Tuple(
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
