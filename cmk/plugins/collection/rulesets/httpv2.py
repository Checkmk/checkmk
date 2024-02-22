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
    Dictionary,
    FixedValue,
    InputHint,
    Integer,
    LevelDirection,
    Levels,
    List,
    MatchingScope,
    Password,
    Proxy,
    RegularExpression,
    SIMagnitude,
    SingleChoice,
    SingleChoiceElement,
    String,
    TimeMagnitude,
    TimeSpan,
    validators,
)
from cmk.rulesets.v1.rule_specs import ActiveCheck, EvalType, Topic

_DAY = 24.0 * 3600.0


def _valuespec_response() -> Dictionary:
    return Dictionary(
        title=Title("Status code"),
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
        title=Title("Document"),
        elements={
            "document_body": DictElement(
                parameter_form=SingleChoice(
                    title=Title("Document body"),
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
                    help_text=Help("Note: this still does an HTTP GET or POST, not a HEAD."),
                ),
                required=True,
            ),
            "max_age": DictElement(
                parameter_form=TimeSpan(
                    title=Title("Age"),
                    displayed_magnitudes=[
                        TimeMagnitude.SECOND,
                        TimeMagnitude.MINUTE,
                        TimeMagnitude.HOUR,
                        TimeMagnitude.DAY,
                    ],
                    label=Label("Warn, if the age is older than"),
                    help_text=Help("Warn, if the age of the page is older than this"),
                    prefill=DefaultValue(_DAY),
                ),
            ),
            "page_size": DictElement(
                parameter_form=Dictionary(
                    title=Title("Size"),
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
                            parameter_form=RegularExpression(
                                label=Label("Header name pattern"),
                                predefined_help_text=MatchingScope.INFIX
                                # maxlen=1023,
                            ),
                            required=True,
                        ),
                        "header_value_pattern": DictElement[str](
                            parameter_form=RegularExpression(
                                label=Label("Header value pattern"),
                                predefined_help_text=MatchingScope.INFIX
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


def _send_data(http_method: str | None = None) -> FixedValue | Dictionary:
    if not http_method:
        return FixedValue(
            value=None,
            label=Label("No additional configuration options for this method."),
        )

    return Dictionary(
        elements={
            "body_text": DictElement(
                parameter_form=String(
                    title=Title("Data to send"),
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
                            title=Title("Type selection"),
                            parameter_form=SingleChoice(
                                title=Title("Select type from list"),
                                elements=[
                                    SingleChoiceElement(
                                        name="application_json",
                                        title=Title("application/json"),
                                    ),
                                    SingleChoiceElement(
                                        name="application_octet_stream",
                                        title=Title("application/octet-stream"),
                                    ),
                                    SingleChoiceElement(
                                        name="application_xml",
                                        title=Title("application/xml"),
                                    ),
                                    SingleChoiceElement(
                                        name="application_zip",
                                        title=Title("application/zip"),
                                    ),
                                    SingleChoiceElement(
                                        name="text_csv",
                                        title=Title("text/csv"),
                                    ),
                                    SingleChoiceElement(
                                        name="text_plain",
                                        title=Title("text/plain"),
                                    ),
                                    SingleChoiceElement(
                                        name="text_xml",
                                        title=Title("text/xml"),
                                    ),
                                    SingleChoiceElement(
                                        name="text_html",
                                        title=Title("text/html"),
                                    ),
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
    )


header_dict_elements = {
    "header_name": DictElement(parameter_form=String(label=Label("Name")), required=True),
    "header_value": DictElement(parameter_form=String(label=Label("Value")), required=True),
}


def _valuespec_connection() -> Dictionary:
    return Dictionary(
        title=Title("Connection details"),
        elements={
            # Not yet implemented
            #    "virtual_host": DictElement(
            #        Text(
            #        title=Title("Virtual host"),
            #        size=80,
            #        input_hint="www.mydomain.de",
            #    ),
            # ),
            "http_versions": DictElement(
                parameter_form=SingleChoice(
                    title=Title("HTTP version"),
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
                    elements={
                        "min_version": DictElement(
                            parameter_form=SingleChoice(
                                elements=[
                                    SingleChoiceElement(name="auto", title=Title("Negotiate")),
                                    SingleChoiceElement(
                                        name="tls_1_3", title=Title("Enforce TLS v1.3")
                                    ),
                                    SingleChoiceElement(
                                        name="tls_1_2", title=Title("Enforce TLS v1.2")
                                    ),
                                    SingleChoiceElement(
                                        name="tls_1_1", title=Title("Enforce TLS v1.1")
                                    ),
                                    SingleChoiceElement(
                                        name="tls_1_0", title=Title("Enforce TLS v1.0")
                                    ),
                                ],
                            ),
                            required=True,
                        ),
                        "allow_higher": DictElement(
                            parameter_form=BooleanChoice(label=Label("Allow higher versions")),
                            required=True,
                        ),
                    },
                ),
            ),
            "method": DictElement(
                parameter_form=CascadingSingleChoice(
                    title=Title("HTTP method"),
                    prefill=DefaultValue("get"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="get", title=Title("GET"), parameter_form=_send_data("GET")
                        ),
                        CascadingSingleChoiceElement(
                            name="post",
                            title=Title("POST"),
                            parameter_form=_send_data("POST"),
                        ),
                        CascadingSingleChoiceElement(
                            name="put", title=Title("PUT"), parameter_form=_send_data("PUT")
                        ),
                        CascadingSingleChoiceElement(
                            name="delete",
                            title=Title("DELETE"),
                            parameter_form=_send_data("DELETE"),
                        ),
                        CascadingSingleChoiceElement(
                            name="options",
                            title=Title("OPTIONS"),
                            parameter_form=_send_data(),
                        ),
                        CascadingSingleChoiceElement(
                            name="trace",
                            title=Title("TRACE"),
                            parameter_form=_send_data(),
                        ),
                        CascadingSingleChoiceElement(
                            name="head",
                            title=Title("HEAD"),
                            parameter_form=_send_data(),
                        ),
                        CascadingSingleChoiceElement(
                            name="connect",
                            title=Title("CONNECT"),
                            parameter_form=_send_data("Connect"),
                        ),
                        CascadingSingleChoiceElement(
                            name="connect_post",
                            title=Title("CONNECT:POST"),
                            parameter_form=_send_data(),
                        ),
                        CascadingSingleChoiceElement(
                            name="propfind",
                            title=Title("PROPFIND"),
                            parameter_form=_send_data(),
                        ),
                    ],
                ),
            ),
            "proxy": DictElement(parameter_form=Proxy()),
            "redirects": DictElement(
                parameter_form=SingleChoice(
                    title=Title("Redirects"),
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
                            title=Title("Follow, but stay to same IP-address and port"),
                        ),
                    ],
                    prefill=DefaultValue("follow"),
                ),
            ),
            "timeout": DictElement(
                parameter_form=TimeSpan(
                    title=Title("Connection timeout"),
                    displayed_magnitudes=[TimeMagnitude.SECOND, TimeMagnitude.MILLISECOND],
                    prefill=DefaultValue(10),
                ),
            ),
            "user_agent": DictElement(
                parameter_form=String(
                    title=Title("User Agent"),
                    prefill=DefaultValue("checkmk/check_http"),
                    help_text=Help('String to be sent in http header as "User Agent"'),
                ),
            ),
            "add_headers": DictElement(
                parameter_form=List(
                    title=Title("Additional header lines"),
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
                                            custom_validate=validators.DisallowEmpty(),
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
                                        parameter_form=String(title=Title("API key header")),
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
        title=Title("String validation"),
        elements={
            "header": DictElement(
                parameter_form=CascadingSingleChoice(
                    title=Title("Header"),
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
                    title=Title("Body"),
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
        title=(Title("Standard settings") if is_standard else Title("Individual settings")),
        elements={
            "connection": DictElement(parameter_form=_valuespec_connection()),
            "response_time": DictElement(
                parameter_form=Levels(
                    title=Title("Response time"),
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=[TimeMagnitude.SECOND, TimeMagnitude.MILLISECOND],
                    ),
                    level_direction=LevelDirection.UPPER,
                    predictive=None,
                    help_text=Help("Maximum time the request may take."),
                    prefill_fixed_levels=DefaultValue((0.1, 0.2)),
                ),
            ),
            "server_response": DictElement(parameter_form=_valuespec_response()),
            "cert": DictElement(
                parameter_form=CascadingSingleChoice(
                    title=Title("Certificate validity"),
                    prefill=DefaultValue("validate"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="validate",
                            title=Title("Certificate validity"),
                            parameter_form=Levels[float](
                                title=Title("Check validity"),
                                form_spec_template=TimeSpan(
                                    displayed_magnitudes=(TimeMagnitude.DAY,)
                                ),
                                level_direction=LevelDirection.LOWER,
                                prefill_fixed_levels=InputHint((90.0 * _DAY, 60.0 * _DAY)),
                                predictive=None,
                                help_text=Help(
                                    "Minimum number of days a certificate has to be valid."
                                ),
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="no_validation",
                            title=Title("Do not check certificate"),
                            parameter_form=FixedValue(
                                value=None,
                                title=Title("Do not check certificate"),
                            ),
                        ),
                    ],
                )
            ),
            "document": DictElement(parameter_form=_valuespec_document()),
            "content": DictElement(parameter_form=_valuespec_content()),
        },
    )


def _valuespec_endpoints() -> List:
    return List(
        title=Title("Endpoints"),
        custom_validate=validators.DisallowEmpty(),
        element_template=Dictionary(
            elements={
                "service_name": DictElement(
                    parameter_form=Dictionary(
                        title=Title("Service description"),
                        elements={
                            "prefix": DictElement(
                                parameter_form=SingleChoice(
                                    title=Title("Prefix"),
                                    elements=[
                                        SingleChoiceElement(
                                            name="auto",
                                            title=Title("Use protocol name: HTTP(S)"),
                                        ),
                                        SingleChoiceElement(
                                            name="none",
                                            title=Title("Do not use a prefix"),
                                        ),
                                    ],
                                ),
                                required=True,
                            ),
                            "name": DictElement(
                                parameter_form=String(
                                    title=Title("Name"),
                                    custom_validate=validators.DisallowEmpty(),
                                    prefill=InputHint("My HTTP service"),
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
                        prefill=InputHint("https://subdomain.domain.tld:port/path/to/filename"),
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
            "standard_settings": DictElement(parameter_form=_valuespec_settings()),
        },
    )


rule_spec_httpv2 = ActiveCheck(
    title=Title("Check HTTP web service"),
    topic=Topic.NETWORKING,
    eval_type=EvalType.MERGE,
    name="httpv2",
    parameter_form=_form_active_checks_httpv2,
)
