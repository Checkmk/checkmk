#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping
from typing import Any

# mypy: disable-error-code="exhaustive-match"
# mypy: disable-error-code="type-arg"
from cmk.rulesets.internal.form_specs import InternalProxy, migrate_to_internal_proxy
from cmk.rulesets.v1 import Help, Label, Message, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DataSize,
    DefaultValue,
    DictElement,
    DictGroup,
    Dictionary,
    FieldSize,
    FixedValue,
    InputHint,
    Integer,
    LevelDirection,
    List,
    MatchingScope,
    Password,
    RegularExpression,
    ServiceState,
    SIMagnitude,
    SimpleLevels,
    SimpleLevelsConfigModel,
    SingleChoice,
    SingleChoiceElement,
    String,
    TimeMagnitude,
    TimeSpan,
    validators,
)
from cmk.rulesets.v1.rule_specs import ActiveCheck, Topic

from ..server_side_calls.httpv2 import TlsVersion

_DAY = 24.0 * 3600.0
_DEFAULT_USER_AGENT = "checkmk-active-httpv2/2.4.0"


def _valuespec_response() -> Dictionary:
    return Dictionary(
        title=Title("Status code"),
        help_text=Help(
            "You may set expected status codes that should be returned by the request. The service will be WARN if the actual status code does not match any of the expected ones."
        ),
        elements={
            "expected": DictElement(
                parameter_form=List(
                    title=Title("Expected"),
                    element_template=Integer(prefill=DefaultValue(200)),
                ),
                required=True,
            ),
            # TODO Not yet implemented
            # NOTE: (mo) There will be no ListOfStrings; use List[str] instead.
            # "ignored": ListOfStrings(
            #        title=Title("Ignored"),
            #        orientation="horizontal",
            #        default_value=["307"],
            #    ),
            # ),
        },
    )


def _valuespec_document() -> Dictionary:
    return Dictionary(
        title=Title("How to handle the document"),
        elements={
            "document_body": DictElement(
                parameter_form=SingleChoice(
                    help_text=Help(
                        "As an alternative to fetch the complete document including the actual web site or application (document body), you may also choose to fetch only the header. Please note, that in this case still the HTTP methods GET or POST will be used by default and not HEAD."
                    ),
                    prefill=DefaultValue("fetch"),
                    elements=[
                        SingleChoiceElement(
                            name="fetch",
                            title=Title("Wait for document body"),
                        ),
                        SingleChoiceElement(
                            name="ignore",
                            title=Title("Get header only"),
                        ),
                    ],
                ),
                required=True,
            ),
            "max_age": DictElement(
                parameter_form=TimeSpan(
                    title=Title("Check document age"),
                    help_text=Help(
                        "Many web services provide a date for the document and the difference to now is the age of the document. The age may be monitored by this option. You will get a WARN if the document is older than the configured threshold."
                    ),
                    displayed_magnitudes=[
                        TimeMagnitude.SECOND,
                        TimeMagnitude.MINUTE,
                        TimeMagnitude.HOUR,
                        TimeMagnitude.DAY,
                    ],
                    label=Label("Warn, if the age is older than"),
                    prefill=DefaultValue(_DAY),
                ),
            ),
            "page_size": DictElement(
                parameter_form=Dictionary(
                    title=Title("Check document size"),
                    help_text=Help(
                        "Choose this option if you need to have the provided document within a specific range of size. You will get a WARN if the size of the actual document is above or below the thresholds."
                    ),
                    elements={
                        "min": DictElement(
                            parameter_form=DataSize(
                                title=Title("Minimum"),
                                displayed_magnitudes=[
                                    SIMagnitude.BYTE,
                                    SIMagnitude.KILO,
                                    SIMagnitude.MEGA,
                                ],
                            ),
                            required=False,
                        ),
                        "max": DictElement(
                            parameter_form=DataSize(
                                title=Title("Maximum"),
                                displayed_magnitudes=[
                                    SIMagnitude.BYTE,
                                    SIMagnitude.KILO,
                                    SIMagnitude.MEGA,
                                ],
                            ),
                            required=False,
                        ),
                    },
                ),
            ),
        },
    )


def _valuespec_expected_regex_header() -> Dictionary:
    return Dictionary(
        title=Title("Regular expressions to expect"),
        elements={
            # TODO max len
            "regex": DictElement(
                parameter_form=Dictionary(
                    elements={
                        "header_name_pattern": DictElement[str](
                            group=DictGroup(),
                            parameter_form=RegularExpression(
                                label=Label("Header name pattern"),
                                predefined_help_text=MatchingScope.INFIX,
                                # maxlen=1023,
                            ),
                            required=True,
                        ),
                        "header_value_pattern": DictElement[str](
                            group=DictGroup(),
                            parameter_form=RegularExpression(
                                label=Label("Header value pattern"),
                                predefined_help_text=MatchingScope.INFIX,
                                # maxlen=1023,
                            ),
                            required=True,
                        ),
                    },
                ),
                required=True,
            ),
            "case_insensitive": DictElement(
                parameter_form=BooleanChoice(
                    label=Label("Case insensitive matching (only applies to header value pattern)")
                ),
                required=True,
            ),
            "invert": DictElement(
                parameter_form=BooleanChoice(label=Label("return CRITICAL if found, OK if not")),
                required=True,
            ),
        },
    )


def _valuespec_expected_regex_body() -> Dictionary:
    return Dictionary(
        title=Title("Regular expression to expect"),
        elements={
            # TODO max len
            "regex": DictElement[str](
                parameter_form=RegularExpression(
                    label=Label("Pattern"),
                    predefined_help_text=MatchingScope.INFIX,
                    # maxlen=1023,
                ),
                required=True,
            ),
            "case_insensitive": DictElement(
                parameter_form=BooleanChoice(label=Label("Case insensitive matching")),
                required=True,
            ),
            "multiline": DictElement(
                parameter_form=BooleanChoice(
                    label=Label("Line-based matching"),
                    help_text=Help(
                        'When checked, the anchors "^" and "$" match on every line, while '
                        '"*" doesn\'t match on newline characters'
                    ),
                ),
                required=True,
            ),
            "invert": DictElement(
                parameter_form=BooleanChoice(label=Label("Return CRITICAL if found, OK if not")),
                required=True,
            ),
        },
    )


def _no_send_data() -> FixedValue:
    return FixedValue(
        value=None,
        label=Label("No additional configuration options for this method."),
    )


def _send_data() -> Dictionary:
    return Dictionary(
        elements={
            "send_data": DictElement(
                parameter_form=Dictionary(
                    title=Title("Send data"),
                    elements={
                        "content": DictElement(
                            parameter_form=String(
                                title=Title("Content"),
                                help_text=Help("Please make sure, that the data is URL-encoded."),
                            ),
                            required=True,
                        ),
                        "content_type": DictElement(
                            parameter_form=CascadingSingleChoice(
                                title=Title("Content-Type"),
                                prefill=DefaultValue("common"),
                                elements=[
                                    CascadingSingleChoiceElement(
                                        name="common",
                                        title=Title("Select type from list"),
                                        parameter_form=SingleChoice(
                                            elements=[
                                                SingleChoiceElement(
                                                    name=content_type.lower()
                                                    .replace("/", "_")
                                                    .replace("-", "_"),
                                                    title=Title("%s") % content_type,
                                                )
                                                for content_type in [
                                                    "application/json",
                                                    "application/xml",
                                                    "application/x-www-form-urlencoded",
                                                    "text/plain",
                                                    "text/xml",
                                                    "text/html",
                                                ]
                                            ],
                                        ),
                                    ),
                                    CascadingSingleChoiceElement(
                                        name="custom",
                                        title=Title("Use custom type"),
                                        parameter_form=String(
                                            prefill=InputHint("text/plain"),
                                        ),
                                    ),
                                ],
                            ),
                            required=True,
                        ),
                    },
                ),
            )
        },
    )


header_dict_elements = {
    "header_name": DictElement(
        group=DictGroup(),
        parameter_form=String(label=Label("Name"), prefill=InputHint("Accept-Language")),
        required=True,
    ),
    "header_value": DictElement(
        group=DictGroup(),
        parameter_form=String(label=Label("Value"), prefill=InputHint("en-US,en;q=0.5")),
        required=True,
    ),
}


def validate_tls_versions(value: Mapping[str, Any]) -> None:
    if value["compatibility_mode"] and value["min_version"] == TlsVersion.TLS_1_3:
        raise validators.ValidationError(
            Message(
                "Enforce TLS 1.3 is not supported in compatibility mode. "
                "Please select a lower minimum TLS version or disable compatibility mode."
            )
        )


def migrate_tls_versions_compatibility_mode(params: object) -> Mapping[str, object]:
    if not isinstance(params, dict):
        raise TypeError(f"Invalid parameters: {params!r}")

    if "compatibility_mode" in params:
        return params

    params["compatibility_mode"] = False
    return params


def _valuespec_connection() -> Dictionary:
    return Dictionary(
        title=Title("Connection buildup"),
        help_text=Help(
            "Options in this group define how the connection to the web server is established."
        ),
        elements={
            "method": DictElement(
                parameter_form=CascadingSingleChoice(
                    title=Title("HTTP method"),
                    prefill=DefaultValue("get"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="get",
                            title=Title("GET"),
                            parameter_form=_no_send_data(),
                        ),
                        CascadingSingleChoiceElement(
                            name="head",
                            title=Title("HEAD"),
                            parameter_form=_no_send_data(),
                        ),
                        CascadingSingleChoiceElement(
                            name="post",
                            title=Title("POST"),
                            parameter_form=_send_data(),
                        ),
                        CascadingSingleChoiceElement(
                            name="put",
                            title=Title("PUT"),
                            parameter_form=_send_data(),
                        ),
                        CascadingSingleChoiceElement(
                            name="delete",
                            title=Title("DELETE"),
                            parameter_form=_no_send_data(),
                        ),
                    ],
                ),
                required=True,
            ),
            "http_versions": DictElement(
                parameter_form=SingleChoice(
                    title=Title("HTTP version"),
                    help_text=Help(
                        "You may enforce a specific version if you need to test the compatibility "
                        "with one or another version. Please note that the "
                        "connection will fail if the web server does not support the required "
                        "HTTP version."
                    ),
                    prefill=DefaultValue("auto"),
                    elements=[
                        SingleChoiceElement(
                            name="auto",
                            title=Title("Negotiate"),
                        ),
                        SingleChoiceElement(
                            name="http_2",
                            title=Title("Use HTTP/2"),
                        ),
                        SingleChoiceElement(name="http_1_1", title=Title("Use HTTP/1.1")),
                    ],
                ),
            ),
            "tls_versions": DictElement(
                parameter_form=Dictionary(
                    title=Title("TLS version"),
                    custom_validate=[validate_tls_versions],
                    migrate=migrate_tls_versions_compatibility_mode,
                    help_text=Help(
                        "You may choose to enforce the usage of a specific TLS version. "
                        "Either by pinning to exactly the selected version, or by also allowing "
                        "higher versions. Please note Checkmk does not support SSLv3 or SSLv2 "
                        "at all. TLS 1.0 and 1.1 is supported by the underlying plug-in but not "
                        "on this rule set as the plug-in needs to be called with an unsafe "
                        "configuration of OpenSSL 3. This requires a direct call via "
                        "<i>Integrate Nagios plug-ins.</i>"
                    ),
                    elements={
                        "min_version": DictElement(
                            group=DictGroup(),
                            parameter_form=SingleChoice(
                                elements=[
                                    SingleChoiceElement(name="auto", title=Title("Negotiate")),
                                    SingleChoiceElement(
                                        name="tls_1_3", title=Title("Enforce TLS v1.3")
                                    ),
                                    SingleChoiceElement(
                                        name="tls_1_2", title=Title("Enforce TLS v1.2")
                                    ),
                                ],
                            ),
                            required=True,
                        ),
                        "allow_higher": DictElement(
                            group=DictGroup(),
                            parameter_form=BooleanChoice(label=Label("Allow higher versions")),
                            required=True,
                        ),
                        "compatibility_mode": DictElement(
                            parameter_form=BooleanChoice(
                                label=Label("Enable compatibility mode"),
                                help_text=Help(
                                    "Enable this option if you encounter TLS connection failures with this check "
                                    "while other tools like cURL or the legacy check_http succeed. The default TLS "
                                    "backend (rustls) is more restrictive and strictly adheres to TLS standards. "
                                    "Enabling compatibility mode switches to a less restrictive TLS backend (native-tls) "
                                    "that behaves similarly to cURL and other common tools."
                                ),
                            ),
                            required=True,
                        ),
                    },
                ),
            ),
            "proxy": DictElement(parameter_form=InternalProxy(migrate=migrate_to_internal_proxy)),
            "address_family": DictElement(
                parameter_form=SingleChoice(
                    title=Title("IP address family"),
                    help_text=Help(
                        "The check will use any IP address protocol by default. Selecting a "
                        "specific protocol or use the primary of a host will enforce the usage "
                        "of your choice. This gives you more control if you want to ensure the "
                        "availability of you web endpoint through either IPv4 or IPv6."
                    ),
                    prefill=DefaultValue("any"),
                    elements=[
                        SingleChoiceElement("any", Title("Use any network address")),
                        SingleChoiceElement("ipv4", Title("Enforce IPv4")),
                        SingleChoiceElement("ipv6", Title("Enforce IPv6")),
                        SingleChoiceElement("primary", Title("Enforce primary address family")),
                    ],
                ),
            ),
            "redirects": DictElement(
                parameter_form=SingleChoice(
                    title=Title("How to handle redirects"),
                    help_text=Help(
                        "The check will follow redirects on default. By activating this option, "
                        "you can enforce a specific behavior or set a specific state in case "
                        "of a redirect."
                    ),
                    elements=[
                        SingleChoiceElement(
                            name="ok",
                            title=Title("Make check OK"),
                        ),
                        SingleChoiceElement(
                            name="warning",
                            title=Title("Make check WARNING"),
                        ),
                        SingleChoiceElement(
                            name="critical",
                            title=Title("Make check CRITICAL"),
                        ),
                        SingleChoiceElement(
                            name="follow",
                            title=Title("Follow the redirection"),
                        ),
                        SingleChoiceElement(
                            name="sticky",
                            title=Title("Follow, but stay to same IP address"),
                        ),
                        SingleChoiceElement(
                            name="stickyport",
                            title=Title("Follow, but stay to same IP address and port"),
                        ),
                    ],
                    prefill=DefaultValue("follow"),
                ),
            ),
            "timeout": DictElement(
                parameter_form=TimeSpan(
                    title=Title("Connection timeout"),
                    displayed_magnitudes=[
                        TimeMagnitude.SECOND,
                        TimeMagnitude.MILLISECOND,
                    ],
                    help_text=Help(
                        "The result will be treated as connection failure if the threshold gets "
                        "reached and leads to a CRIT on the service."
                    ),
                    prefill=DefaultValue(10),
                ),
            ),
            "user_agent": DictElement(
                parameter_form=String(
                    title=Title("User agent"),
                    help_text=Help(
                        "To make the querying source transparent for the requested web server, the "
                        "user agent header field will be used. The default is set to "
                        "checkmk/check_http, but you may use your own. The entry needs to be a "
                        "valid string for a header value."
                    ),
                    prefill=DefaultValue(_DEFAULT_USER_AGENT),
                    macro_support=True,
                ),
            ),
            "add_headers": DictElement(
                parameter_form=List(
                    title=Title("Additional header lines"),
                    help_text=Help(
                        "These additional header lines will be used in the request. You may use "
                        "any header lines that follow the conventions for header entries. Please "
                        "note that you don't need a colon to separate key and value as you have "
                        "a dedicated input field for each."
                    ),
                    element_template=Dictionary(elements=header_dict_elements),
                ),
            ),
            "auth": DictElement(
                parameter_form=CascadingSingleChoice(
                    title=Title("Authentication"),
                    prefill=DefaultValue("user_auth"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="user_auth",
                            title=Title("User based authentication"),
                            parameter_form=Dictionary(
                                title=Title("User based authentication"),
                                help_text=Help("Credentials for HTTP Basic Authentication"),
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
                                        ),
                                        required=True,
                                    ),
                                },
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="token_auth",
                            title=Title("Token based authentication"),
                            parameter_form=Dictionary(
                                title=Title("Token based authentication"),
                                elements={
                                    "header": DictElement(
                                        parameter_form=String(
                                            title=Title("API key header"),
                                            prefill=InputHint("Authorization"),
                                        ),
                                        required=True,
                                    ),
                                    "token": DictElement(
                                        parameter_form=Password(title=Title("API key")),
                                        required=True,
                                    ),
                                },
                            ),
                        ),
                    ],
                ),
            ),
        },
    )


def _valuespec_content() -> Dictionary:
    return Dictionary(
        title=Title("Search for strings"),
        help_text=Help(
            "Provide fixed string or regular expression conditions for the HTTP reponse."
            " If the response fails the condition (E.g., expected string not found in body),"
            " this will result in a CRITICAL state."
        ),
        elements={
            "header": DictElement(
                parameter_form=CascadingSingleChoice(
                    title=Title("Search for header"),
                    help_text=Help(
                        "The provided header key and value need to match exactly with the "
                        "actual header of the response. Please note that the service will "
                        "get a CRIT, if either the key or the value does not match. If searching "
                        "for a regular expression, the first match is considered a success."
                    ),
                    prefill=DefaultValue("string"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="string",
                            title=Title("Fixed string"),
                            parameter_form=Dictionary(
                                title=Title("Fixed string"),
                                elements=header_dict_elements,
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="regex",
                            title=Title("Regular expression"),
                            parameter_form=_valuespec_expected_regex_header(),
                        ),
                    ],
                ),
            ),
            "body": DictElement(
                parameter_form=CascadingSingleChoice(
                    title=Title("Search in body"),
                    help_text=Help(
                        "The provided string to be looked for needs to be exactly the same as in "
                        "the raw document body. This includes html markups between user-oriented "
                        "strings. This is also true for searching in a regular expression."
                    ),
                    prefill=DefaultValue("string"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="string",
                            title=Title("Fixed string"),
                            parameter_form=String(
                                title=Title("Fixed string"),
                                macro_support=True,
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="regex",
                            title=Title("Regular expression"),
                            parameter_form=_valuespec_expected_regex_body(),
                        ),
                    ],
                )
            ),
            "fail_state": DictElement(
                parameter_form=ServiceState(
                    title=Title("Service state for failing text search condition."),
                    help_text=Help(
                        "If the configured string/regex searches fail, this will result in a CRIT "
                        "state by default. Here you can choose an alternative state that will apply "
                        "to all configured string/regex searches when failing their condition."
                    ),
                    prefill=DefaultValue(ServiceState.CRIT),
                ),
            ),
        },
    )


def _migrate_to_cascading(params: object) -> tuple[str, object]:
    match params:
        case "validate", tuple(value):
            return "validate", value
        case "no_validation", None:
            return "no_validation", None
        case "fixed", tuple(value):
            return "validate", ("fixed", value)
        case "no_levels", None:
            return "validate", ("no_levels", None)
    raise TypeError(f"Invalid certificate levels: {params!r}")


# This could change later, so we need to distinct between standard settings and
# individual settings (currently referred as "shared_settings")
def _valuespec_settings(is_standard: bool = True) -> Dictionary:
    return Dictionary(
        title=(
            Title("Standard settings for all endpoints")
            if is_standard
            else Title("Individual settings to use for this endpoint")
        ),
        help_text=Help(
            "Standard settings are used for all endpoints unless overwritten by the "
            "individual settings of an endpoint."
        ),
        elements={
            "server": DictElement(
                parameter_form=String(
                    title=Title("Connect to specific host"),
                    help_text=Help(
                        "You may enter any fully qualified domain name or valid "
                        "IP address here if you need to connect to a different server rather "
                        "than the one specified in the URL. The name must not contain any further "
                        "information, like port or protocol. You may use macros in "
                        "this field. The most common ones are $HOSTNAME$, $HOSTALIAS$ "
                        "or $HOSTADDRESS$."
                    ),
                    prefill=InputHint("192.168.0.73 or my.host.tld"),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
            ),
            "connection": DictElement(parameter_form=_valuespec_connection()),
            "response_time": DictElement[SimpleLevelsConfigModel[float]](
                parameter_form=SimpleLevels[float](
                    title=Title("Response time"),
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=[
                            TimeMagnitude.SECOND,
                            TimeMagnitude.MILLISECOND,
                        ],
                    ),
                    level_direction=LevelDirection.UPPER,
                    help_text=Help(
                        "This options sets a maximum time the request may take. The request will be canceled after the set time expired."
                    ),
                    prefill_fixed_levels=DefaultValue((0.1, 0.2)),
                ),
            ),
            "server_response": DictElement(parameter_form=_valuespec_response()),
            "cert": DictElement(
                parameter_form=CascadingSingleChoice(
                    title=Title("Certificate validity"),
                    help_text=Help(
                        "By default the certificate validity in general will be checked. With "
                        "this option you can choose to check additionally for the remeinaing time "
                        "the certificate will be valid or ignore the certificate completely. "
                        "Please use the latter as last resort and with caution!"
                    ),
                    prefill=DefaultValue("validate"),
                    migrate=_migrate_to_cascading,
                    elements=[
                        CascadingSingleChoiceElement(
                            name="validate",
                            title=Title("Check certificate"),
                            parameter_form=SimpleLevels[float](
                                form_spec_template=TimeSpan(
                                    displayed_magnitudes=[TimeMagnitude.DAY]
                                ),
                                level_direction=LevelDirection.LOWER,
                                prefill_fixed_levels=DefaultValue((40.0 * _DAY, 20.0 * _DAY)),
                                help_text=Help(
                                    "Minimum number of days a certificate has to be valid."
                                ),
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="no_validation",
                            title=Title("Ignore certificate"),
                            parameter_form=FixedValue(
                                value=None,
                                help_text=Help(
                                    "If invalid certificates are trusted, any certificate for any "
                                    "site will be trusted for use. This includes expired "
                                    "certificates and introduces significant vulnerabilities such "
                                    "as man-in-the-middle attacks. Please use this option as a "
                                    "last resort and ideally in combination with an independent "
                                    "certificate check."
                                ),
                            ),
                        ),
                    ],
                ),
            ),
            "document": DictElement(parameter_form=_valuespec_document()),
            "content": DictElement(parameter_form=_valuespec_content()),
        },
    )


def _valuespec_endpoints() -> List:
    return List(
        title=Title("HTTP web service endpoints to monitor"),
        help_text=Help(
            "Each endpoint will result in its own service. If not specified or explicitly "
            "overwritten below the endpoint, all standard settings will be used. You need "
            "to specify at least one endpoint to monitor."
        ),
        add_element_label=Label("Add new endpoint"),
        custom_validate=(validators.LengthInRange(min_value=1),),
        element_template=Dictionary(
            elements={
                "service_name": DictElement(
                    parameter_form=Dictionary(
                        title=Title("Service name"),
                        elements={
                            "prefix": DictElement(
                                group=DictGroup(),
                                parameter_form=SingleChoice(
                                    title=Title("Prefix"),
                                    help_text=Help(
                                        "The prefix is automatically added to each service to be able to organize it. The prefix is static and will be HTTP for unencrypted endpoints and HTTPS if TLS encryption is used. Alternatively, you may choose not to use the prefix option."
                                    ),
                                    elements=[
                                        SingleChoiceElement(
                                            name="auto",
                                            title=Title('Use "HTTP(S)" as service name prefix'),
                                        ),
                                        SingleChoiceElement(
                                            name="none",
                                            title=Title("Do not use a prefix"),
                                        ),
                                    ],
                                    prefill=DefaultValue("auto"),
                                ),
                                required=True,
                            ),
                            "name": DictElement(
                                group=DictGroup(),
                                parameter_form=String(
                                    title=Title("Name"),
                                    help_text=Help(
                                        "The name is the individual part of the used service name. Choose a human readable and unique title to be able to find your service later in Checkmk."
                                    ),
                                    custom_validate=(validators.LengthInRange(min_value=1),),
                                    prefill=InputHint("My service name"),
                                    macro_support=True,
                                ),
                                required=True,
                            ),
                        },
                    ),
                    required=True,
                ),
                "url": DictElement(
                    parameter_form=String(
                        title=Title("URL"),
                        field_size=FieldSize.LARGE,
                        help_text=Help(
                            "The URL to monitor. This URL must include the protocol (HTTP or "
                            "HTTPS), the full address and, if needed, also the port of the endpoint "
                            "if using a non standard port. The URL may also include query "
                            "parameters or anchors. You may use macros in this field. The most "
                            "common ones are $HOSTNAME$, $HOSTALIAS$ or $HOSTADDRESS$. "
                            "Please note, that authentication must "
                            "not be added here as it exposes sensible information. Use "
                            "'authentication' in the connection buildup options, instead. "
                        ),
                        prefill=InputHint(
                            "https://subdomain.domain.tld:port/path/to/filename?parameter=value#anchor"
                        ),
                        custom_validate=(
                            validators.Url(
                                [
                                    validators.UrlProtocol.HTTP,
                                    validators.UrlProtocol.HTTPS,
                                ],
                            ),
                        ),
                        # macro_support=True, # deactivated to avoid conflicts with manual help_text
                    ),
                    required=True,
                ),
                "individual_settings": DictElement(
                    parameter_form=_valuespec_settings(is_standard=False)
                ),
            },
        ),
    )


def _form_active_checks_httpv2() -> Dictionary:
    return Dictionary(
        elements={
            "endpoints": DictElement(parameter_form=_valuespec_endpoints(), required=True),
            "standard_settings": DictElement(parameter_form=_valuespec_settings(), required=True),
        },
        ignored_elements=("from_v1",),
    )


rule_spec_httpv2 = ActiveCheck(
    title=Title("Check HTTP web service"),
    topic=Topic.NETWORKING,
    name="httpv2",
    parameter_form=_form_active_checks_httpv2,
)
