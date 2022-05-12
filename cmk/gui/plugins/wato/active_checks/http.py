#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy

from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.active_checks.common import (
    ip_address_family_element,
    RulespecGroupActiveChecks,
    transform_cert_days,
)
from cmk.gui.plugins.wato.utils import HostRulespec, IndividualOrStoredPassword, rulespec_registry
from cmk.gui.valuespec import (
    Age,
    CascadingDropdown,
    Checkbox,
    Dictionary,
    DropdownChoice,
    FixedValue,
    Float,
    Integer,
    ListOfStrings,
    RegExp,
    TextInput,
    Transform,
    Tuple,
)


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
            ip_address_family_element(),
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
