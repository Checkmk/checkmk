#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="exhaustive-match"

# mypy: disable-error-code="type-arg"

from cmk.rulesets.v1 import Help, Label, Message, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DataSize,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    InputHint,
    Integer,
    LevelDirection,
    List,
    MatchingScope,
    migrate_to_float_simple_levels,
    migrate_to_password,
    Password,
    RegularExpression,
    SIMagnitude,
    SimpleLevels,
    SingleChoice,
    SingleChoiceElement,
    String,
    TimeMagnitude,
    TimeSpan,
    validators,
)
from cmk.rulesets.v1.rule_specs import ActiveCheck, Topic


def _migrate_to_float(value: object) -> float:
    match value:
        case int(value) | float(value):
            return float(value)
    raise ValueError(value)


def _migrate_ssl_choices(value: object) -> str:
    match value:
        case "1.1":
            return "ssl_1_1"
        case "1.2":
            return "ssl_1_2"
        case "1" | "2" | "3":
            return f"ssl_{value}"
        case "auto" | "ssl_1" | "ssl_2" | "ssl_3" | "ssl_1_1" | "ssl_1_2":
            return str(value)
    raise ValueError(value)


def _migrate_address_family_choices(value: object) -> str:
    match value:
        case "ipv4":
            return "any"
        case "ipv6":
            return "ipv6_enforced"
        case None:
            return "primary_enforced"
        case "any" | "ipv4_enforced" | "ipv6_enforced" | "primary_enforced":
            return str(value)
    raise ValueError(value)


def _migrate_to_auth(value: object) -> dict:
    match value:
        case {**val}:
            return val
        case (str(user), password):
            return {"user": user, "password": password}
    raise ValueError(value)


def _migrate_to_post_data(value: object) -> dict:
    match value:
        case {**val}:
            return val
        case (str(data), str(content_type)):
            return {"data": data, "content_type": content_type}
    raise ValueError(value)


def _migrate_to_page_size(value: object) -> dict:
    match value:
        case {**val}:
            return val
        case (int(minimum), int(maximum)):
            return {"minimum": minimum, "maximum": maximum}
    raise ValueError(value)


def _migrate_to_expect_regex(value: object) -> dict:
    if isinstance(value, dict):
        return value
    if not isinstance(value, tuple):
        raise ValueError(value)
    return {
        "regex": value[0],
        "case_insensitive": value[1],
        "crit_if_found": value[2],
        "multiline": value[3],
    }


def _migrate_http_method(value: object) -> str:
    match value:
        case "CONNECT:POST":
            return "CONNECT_POST"
        case (
            "GET"
            | "POST"
            | "OPTIONS"
            | "TRACE"
            | "PUT"
            | "DELETE"
            | "HEAD"
            | "CONNECT"
            | "CONNECT_POST"
            | "PROPFIND"
        ):
            return str(value)
    raise ValueError(value)


def _active_checks_http_proxyspec() -> Dictionary:
    return Dictionary(
        elements={
            "address": DictElement(
                parameter_form=String(title=Title("Name / IP address"), macro_support=True),
                required=True,
            ),
            "port": DictElement(parameter_form=_active_checks_http_portspec(80)),
            "auth": DictElement(
                parameter_form=Dictionary(
                    title=Title("Basic authorization"),
                    elements={
                        "user": DictElement(
                            parameter_form=String(
                                title=Title("Username"),
                                custom_validate=(validators.LengthInRange(min_value=1),),
                            ),
                            required=True,
                        ),
                        "password": DictElement(
                            parameter_form=Password(
                                title=Title("Password"), migrate=migrate_to_password
                            ),
                            required=True,
                        ),
                    },
                    migrate=_migrate_to_auth,
                ),
            ),
        },
        help_text=Help(
            "For <tt>check_http</tt> to work with a proxy server, you will most likely need use "
            "the HTTP method <tt>CONNECT</tt>. If you configure a proxy, Checkmk will "
            "automatically use this method, unless you explicitly select a different method in the "
            "options below (URL mode only)."
        ),
    )


def _active_checks_http_hostspec() -> Dictionary:
    return Dictionary(
        title=Title("Host settings"),
        help_text=Help(
            "Usually Checkmk will nail this check to the primary IP address of the host it is "
            "attached to. It will use the corresponding IP version (IPv4/IPv6) and default port "
            "(80/443). With this option you can override either of these parameters. By default no "
            "virtual host is set and HTTP/1.0 will be used. In some setups however, you may want "
            "to distinguish the contacted server address from your virtual host name. In this case "
            "the HTTP Host header will be set and HTTP/1.1 is used."
        ),
        elements={
            "address": DictElement(
                parameter_form=CascadingSingleChoice(
                    title=Title("Address (name / IP or proxy) -- see also inline help for proxy"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="direct",
                            title=Title("Host name / IP address"),
                            parameter_form=String(
                                custom_validate=(validators.LengthInRange(min_value=1),),
                                macro_support=True,
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="proxy",
                            title=Title("Proxy server"),
                            parameter_form=_active_checks_http_proxyspec(),
                        ),
                    ],
                    prefill=DefaultValue("direct"),
                ),
            ),
            "port": DictElement(
                parameter_form=_active_checks_http_portspec(443),
            ),
            "address_family": DictElement(
                parameter_form=ip_address_family_http(),
            ),
            "virthost": DictElement(
                parameter_form=String(
                    title=Title("Virtual host"),
                    help_text=Help(
                        "Set this in order to specify the name of mode the virtual host for the "
                        "query."
                    ),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
            ),
        },
    )


def ip_address_family_http() -> SingleChoice:
    return SingleChoice(
        title=Title("IP address family"),
        elements=[
            SingleChoiceElement("any", Title("Use any network address")),
            SingleChoiceElement("ipv4_enforced", Title("Enforce IPv4")),
            SingleChoiceElement("ipv6_enforced", Title("Enforce IPv6")),
            SingleChoiceElement("primary_enforced", Title("Enforce primary address family")),
        ],
        prefill=DefaultValue("any"),
        migrate=_migrate_address_family_choices,
    )


def _active_checks_http_validate_all(value: object) -> None:
    if isinstance(value, dict):
        _name, mode = value["mode"]
        if "proxy" in value and "virthost" in mode:
            msg = Message(
                "Unfortunately, using a proxy and a virtual host is not supported (try '%s')."
            ) % Message("Host settings")
            raise validators.ValidationError(msg)


def _active_checks_http_portspec(default: int) -> Integer:
    return Integer(
        title=Title("TCP Port"),
        prefill=DefaultValue(default),
        custom_validate=(validators.NetworkPort(),),
    )


def _validate_active_check_http_name(value: object) -> None:
    if isinstance(value, str) and value.strip() == "^":
        raise validators.ValidationError(Message("Please provide a valid name"))


def _parameter_form_mode() -> CascadingSingleChoice:
    return CascadingSingleChoice(
        title=Title("Mode of the Check"),
        help_text=Help("Perform a check of the URL or the certificate expiration."),
        elements=[
            CascadingSingleChoiceElement(
                name="url",
                title=Title("Check the URL"),
                parameter_form=Dictionary(
                    title=Title("URL Checking"),
                    elements={
                        "uri": DictElement(
                            parameter_form=String(
                                title=Title("URI to fetch (default is <tt>/</tt>)"),
                                help_text=Help(
                                    "The URI of the request. This should start with"
                                    " '/' and not include the domain"
                                    " (e.g. '/index.html')."
                                ),
                                custom_validate=(validators.LengthInRange(min_value=1),),
                                prefill=DefaultValue("/"),
                                macro_support=True,
                            ),
                        ),
                        "ssl": DictElement(
                            parameter_form=SingleChoice(
                                title=Title("Use SSL/HTTPS for the connection"),
                                elements=[
                                    SingleChoiceElement(
                                        "auto",
                                        Title("Use SSL with auto negotiation"),
                                    ),
                                    SingleChoiceElement(
                                        "ssl_1_2", Title("Use SSL, enforce TLSv1.2")
                                    ),
                                    SingleChoiceElement(
                                        "ssl_1_1", Title("Use SSL, enforce TLSv1.1")
                                    ),
                                    SingleChoiceElement("ssl_1", Title("Use SSL, enforce TLSv1")),
                                    SingleChoiceElement("ssl_2", Title("Use SSL, enforce SSLv2")),
                                    SingleChoiceElement("ssl_3", Title("Use SSL, enforce SSLv3")),
                                ],
                                prefill=DefaultValue("auto"),
                                migrate=_migrate_ssl_choices,
                            ),
                        ),
                        "response_time": DictElement(
                            parameter_form=SimpleLevels(
                                title=Title("Expected response time"),
                                form_spec_template=TimeSpan(
                                    displayed_magnitudes=[
                                        TimeMagnitude.MILLISECOND,
                                        TimeMagnitude.SECOND,
                                    ]
                                ),
                                level_direction=LevelDirection.UPPER,
                                prefill_fixed_levels=DefaultValue((0.1, 0.2)),
                                migrate=lambda v: migrate_to_float_simple_levels(v, 0.001),
                            ),
                        ),
                        "timeout": DictElement(
                            parameter_form=TimeSpan(
                                title=Title("Seconds before connection times out"),
                                prefill=DefaultValue(10),
                                displayed_magnitudes=[TimeMagnitude.SECOND],
                                migrate=_migrate_to_float,
                            ),
                        ),
                        "user_agent": DictElement(
                            parameter_form=String(
                                title=Title("User Agent"),
                                help_text=Help('String to be sent in http header as "User Agent"'),
                                custom_validate=(validators.LengthInRange(min_value=1),),
                            ),
                        ),
                        "add_headers": DictElement(
                            parameter_form=List(
                                title=Title("Additional header lines"),
                                element_template=String(),
                            ),
                        ),
                        "auth": DictElement(
                            parameter_form=Dictionary(
                                title=Title("Authorization"),
                                help_text=Help("Credentials for HTTP basic authentication"),
                                elements={
                                    "user": DictElement(
                                        parameter_form=String(
                                            title=Title("Username"),
                                            custom_validate=(
                                                validators.LengthInRange(min_value=1),
                                            ),
                                        ),
                                        required=True,
                                    ),
                                    "password": DictElement(
                                        parameter_form=Password(
                                            title=Title("Password"),
                                            migrate=migrate_to_password,
                                        ),
                                        required=True,
                                    ),
                                },
                                migrate=_migrate_to_auth,
                            ),
                        ),
                        "onredirect": DictElement(
                            parameter_form=SingleChoice(
                                title=Title("How to handle redirect"),
                                elements=[
                                    SingleChoiceElement("ok", Title("Make check OK")),
                                    SingleChoiceElement("warning", Title("Make check WARNING")),
                                    SingleChoiceElement("critical", Title("Make check CRITICAL")),
                                    SingleChoiceElement("follow", Title("Follow the redirection")),
                                    SingleChoiceElement(
                                        "sticky",
                                        Title("Follow, but stay to same IP address"),
                                    ),
                                    SingleChoiceElement(
                                        "stickyport",
                                        Title("Follow, but stay to same IP address and port"),
                                    ),
                                ],
                                prefill=DefaultValue("follow"),
                            ),
                        ),
                        "expect_response_header": DictElement(
                            parameter_form=String(
                                title=Title("String to expect in response headers"),
                            ),
                        ),
                        "expect_response": DictElement(
                            parameter_form=List(
                                element_template=String(),
                                title=Title("Strings to expect in server response"),
                                help_text=Help(
                                    "At least one of these strings is expected in the first "
                                    "(status) line of the server response (default: "
                                    "<tt>HTTP/1.</tt>). If specified skips all other status line "
                                    "logic (ex: 3xx, 4xx, 5xx processing)"
                                ),
                            ),
                        ),
                        "expect_string": DictElement(
                            parameter_form=String(
                                title=Title("Fixed string to expect in the content"),
                                custom_validate=(validators.LengthInRange(min_value=1),),
                            ),
                        ),
                        "expect_regex": DictElement(
                            parameter_form=Dictionary(
                                title=Title("Regular expression to expect in content"),
                                elements={
                                    "regex": DictElement(
                                        parameter_form=RegularExpression(
                                            label=Label("Regular expression: "),
                                            predefined_help_text=MatchingScope.INFIX,
                                            custom_validate=(
                                                validators.LengthInRange(max_value=1023),
                                            ),
                                        ),
                                        required=True,
                                    ),
                                    "case_insensitive": DictElement(
                                        parameter_form=BooleanChoice(
                                            label=Label("Case insensitive")
                                        ),
                                        required=True,
                                    ),
                                    "crit_if_found": DictElement(
                                        parameter_form=BooleanChoice(
                                            label=Label("return CRITICAL if found, OK if not")
                                        ),
                                        required=True,
                                    ),
                                    "multiline": DictElement(
                                        parameter_form=BooleanChoice(
                                            label=Label("Multiline string matching")
                                        ),
                                        required=True,
                                    ),
                                },
                                migrate=_migrate_to_expect_regex,
                            ),
                        ),
                        "post_data": DictElement(
                            parameter_form=Dictionary(
                                title=Title("Send HTTP POST data"),
                                elements={
                                    "data": DictElement(
                                        parameter_form=String(
                                            title=Title("HTTP POST data"),
                                            help_text=Help(
                                                "Data to send via HTTP POST method. Please make "
                                                "sure that the data is URL-encoded."
                                            ),
                                        ),
                                        required=True,
                                    ),
                                    "content_type": DictElement(
                                        parameter_form=String(
                                            title=Title("Content-Type"),
                                            prefill=DefaultValue("text/html"),
                                        ),
                                        required=True,
                                    ),
                                },
                                migrate=_migrate_to_post_data,
                            ),
                        ),
                        "method": DictElement(
                            parameter_form=SingleChoice(
                                title=Title("HTTP Method"),
                                prefill=DefaultValue("GET"),
                                elements=[
                                    SingleChoiceElement("GET", Title("GET")),
                                    SingleChoiceElement("POST", Title("POST")),
                                    SingleChoiceElement("OPTIONS", Title("OPTIONS")),
                                    SingleChoiceElement("TRACE", Title("TRACE")),
                                    SingleChoiceElement("PUT", Title("PUT")),
                                    SingleChoiceElement("DELETE", Title("DELETE")),
                                    SingleChoiceElement("HEAD", Title("HEAD")),
                                    SingleChoiceElement("CONNECT", Title("CONNECT")),
                                    SingleChoiceElement("CONNECT_POST", Title("CONNECT:POST")),
                                    SingleChoiceElement("PROPFIND", Title("PROPFIND")),
                                ],
                                migrate=_migrate_http_method,
                            ),
                        ),
                        "no_body": DictElement(
                            parameter_form=FixedValue(
                                value=True,
                                title=Title("Don't wait for document body"),
                                help_text=Help(
                                    "Note: this still does an HTTP GET or POST, not a HEAD."
                                ),
                                label=Label("don't wait for body"),
                            ),
                        ),
                        "page_size": DictElement(
                            parameter_form=Dictionary(
                                title=Title("Page size to expect"),
                                elements={
                                    "minimum": DictElement(
                                        parameter_form=DataSize(
                                            title=Title("Minimum"),
                                            displayed_magnitudes=[SIMagnitude.BYTE],
                                        ),
                                        required=True,
                                    ),
                                    "maximum": DictElement(
                                        parameter_form=DataSize(
                                            title=Title("Maximum"),
                                            displayed_magnitudes=[SIMagnitude.BYTE],
                                        ),
                                        required=True,
                                    ),
                                },
                                migrate=_migrate_to_page_size,
                            ),
                        ),
                        "max_age": DictElement(
                            parameter_form=TimeSpan(
                                title=Title("Maximum age"),
                                help_text=Help("Warn, if the age of the page is older than this"),
                                prefill=DefaultValue(3600 * 24),
                                displayed_magnitudes=[
                                    TimeMagnitude.SECOND,
                                    TimeMagnitude.MINUTE,
                                    TimeMagnitude.HOUR,
                                    TimeMagnitude.DAY,
                                ],
                                migrate=_migrate_to_float,
                            ),
                        ),
                        "urlize": DictElement(
                            parameter_form=FixedValue(
                                value=True,
                                title=Title("Clickable URLs"),
                                label=Label("Format check output as hyperlink"),
                                help_text=Help(
                                    "With this option the check produces an output that is a valid"
                                    " hyperlink to the checked URL and this clickable."
                                ),
                            ),
                        ),
                        "extended_perfdata": DictElement(
                            parameter_form=FixedValue(
                                value=True,
                                label=Label("Extended perfdata"),
                                title=Title("Record additional performance data"),
                                help_text=Help(
                                    "This option makes the HTTP check produce more detailed "
                                    "performance data values like the connect time, header time, "
                                    "time till first byte received and the transfer time."
                                ),
                            ),
                        ),
                    },
                ),
            ),
            CascadingSingleChoiceElement(
                name="cert",
                title=Title("Check SSL Certificate Age"),
                parameter_form=Dictionary(
                    title=Title("Certificate Checking"),
                    help_text=Help("Port defaults to 443. In this mode the URL is not checked."),
                    elements={
                        "cert_days": DictElement(
                            parameter_form=SimpleLevels(
                                title=Title("Age"),
                                help_text=Help(
                                    "Minimum number of days a certificate has to be valid."
                                ),
                                level_direction=LevelDirection.LOWER,
                                form_spec_template=TimeSpan(
                                    displayed_magnitudes=[
                                        TimeMagnitude.DAY,
                                    ],
                                    custom_validate=(validators.NumberInRange(min_value=0),),
                                ),
                                prefill_fixed_levels=InputHint((0.0, 0.0)),
                                migrate=lambda x: migrate_to_float_simple_levels(x, 24 * 3600),
                            ),
                            required=True,
                        ),
                    },
                ),
            ),
        ],
        prefill=DefaultValue("url"),
    )


def _parameter_form_active_checks_http() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "Check HTTP/HTTPS service using the plug-in <tt>check_http</tt> from the standard "
            "monitoring plug-ins. This plug-in tests the HTTP service on the specified host. It can "
            "test normal (HTTP) and secure (HTTPS) servers, follow redirects, search for strings "
            "and regular expressions, check connection times, and report on certificate expiration "
            "times. Please note that this plug-in is deprecated and shall not be used anymore. "
            'Please use the new "Check HTTP web service" instead.'
        ),
        elements={
            "name": DictElement(
                parameter_form=String(
                    title=Title("Service name"),
                    help_text=Help(
                        "Will be used in the service name. If the name starts with a caret"
                        " (<tt>^</tt>), the service name will not be prefixed with either"
                        " <tt>HTTP</tt> or <tt>HTTPS</tt>."
                    ),
                    custom_validate=(
                        validators.LengthInRange(min_value=1),
                        _validate_active_check_http_name,
                    ),
                    macro_support=True,
                ),
                required=True,
            ),
            "host": DictElement(parameter_form=_active_checks_http_hostspec(), required=True),
            "mode": DictElement(parameter_form=_parameter_form_mode(), required=True),
            "disable_sni": DictElement(
                parameter_form=FixedValue(
                    value=True,
                    title=Title("Advanced: Disable SSL/TLS host name extension support (SNI)"),
                    help_text=Help(
                        "In earlier versions of Checkmk users had to enable SNI explicitly."
                        " We now assume users allways want SNI support. If you don't, you"
                        " can disable it with this option."
                    ),
                ),
            ),
        },
        custom_validate=(_active_checks_http_validate_all,),
    )


rule_spec_http = ActiveCheck(
    name="http",
    topic=Topic.NETWORKING,
    title=Title("Check HTTP service"),
    parameter_form=_parameter_form_active_checks_http,
    is_deprecated=True,
)
