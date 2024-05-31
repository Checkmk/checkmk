#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DataSize,
    DefaultValue,
    DictElement,
    DictGroup,
    Dictionary,
    FixedValue,
    InputHint,
    Integer,
    LevelDirection,
    List,
    MatchingScope,
    migrate_to_proxy,
    Password,
    Proxy,
    RegularExpression,
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
                parameter_form=BooleanChoice(label=Label("return CRITICAL if found, OK if not")),
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


def _valuespec_connection() -> Dictionary:
    return Dictionary(
        title=Title("Connection buildup"),
        help_text=Help(
            "Options in this group define how the connection to the web server is established."
        ),
        elements={
            # Not yet implemented
            #    "virtual_host": DictElement(
            #        Text(
            #        title=Title("Virtual host"),
            #        size=80,
            #        input_hint="www.mydomain.de",
            #    ),
            # ),
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
                    },
                ),
            ),
            "proxy": DictElement(parameter_form=Proxy(migrate=migrate_to_proxy)),
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
                    displayed_magnitudes=[TimeMagnitude.SECOND, TimeMagnitude.MILLISECOND],
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
        elements={
            "header": DictElement(
                parameter_form=CascadingSingleChoice(
                    title=Title("Search for header"),
                    help_text=Help(
                        "The provided header key and value need to match exactly with the "
                        "actual header of the response. Please note that the service will "
                        "get a WARN if any, the key or the value, is not matching. If searching "
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
                        "The provided string to look for needs to be exact as in the raw document "
                        "body. This includes html markups in between user facing strings. This is "
                        "also true if looking through a regular expression."
                    ),
                    prefill=DefaultValue("string"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="string",
                            title=Title("Fixed string"),
                            parameter_form=String(title=Title("Fixed string")),
                        ),
                        CascadingSingleChoiceElement(
                            name="regex",
                            title=Title("Regular expression"),
                            parameter_form=_valuespec_expected_regex_body(),
                        ),
                    ],
                )
            ),
        },
    )


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
            "connection": DictElement(parameter_form=_valuespec_connection()),
            "response_time": DictElement[SimpleLevelsConfigModel[float]](
                parameter_form=SimpleLevels[float](
                    title=Title("Response time"),
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=[TimeMagnitude.SECOND, TimeMagnitude.MILLISECOND],
                    ),
                    level_direction=LevelDirection.UPPER,
                    help_text=Help(
                        "This options sets a maximum time the request may take. The request will be canceled after the set time expired."
                    ),
                    prefill_fixed_levels=DefaultValue((0.1, 0.2)),
                ),
            ),
            "server_response": DictElement(parameter_form=_valuespec_response()),
            "cert": DictElement[SimpleLevelsConfigModel[float]](
                parameter_form=SimpleLevels[float](
                    title=Title("Certificate validity"),
                    form_spec_template=TimeSpan(displayed_magnitudes=[TimeMagnitude.DAY]),
                    level_direction=LevelDirection.LOWER,
                    prefill_fixed_levels=DefaultValue((40.0 * _DAY, 20.0 * _DAY)),
                    help_text=Help("Minimum number of days a certificate has to be valid."),
                )
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
                                        "The prefix is automatically added to each service to be able to organize them. The prefix is static and will be HTTP for unencrypted endpoints and HTTPS if TLS encryption is used. Alternatively, you may choose not to use the prefix option."
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
                                        "The name is the individual part of the used service description. Choose a human readable and unique title to be able to find your service later in Checkmk."
                                    ),
                                    custom_validate=(validators.LengthInRange(min_value=1),),
                                    prefill=InputHint("My service name"),
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
                        help_text=Help(
                            "The URL to monitor. This URL must include the protocol (HTTP or "
                            "HTTPS), the full address and, if needed, also the port the endpoint "
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
                                [validators.UrlProtocol.HTTP, validators.UrlProtocol.HTTPS],
                            ),
                        ),
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
    )


rule_spec_httpv2 = ActiveCheck(
    title=Title("Check HTTP web service"),
    topic=Topic.NETWORKING,
    name="httpv2",
    parameter_form=_form_active_checks_httpv2,
)
