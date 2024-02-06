#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Localizable
from cmk.rulesets.v1.form_specs import DefaultValue, InputHint
from cmk.rulesets.v1.form_specs.basic import (
    BooleanChoice,
    FixedValue,
    Integer,
    SingleChoice,
    SingleChoiceElement,
    Text,
    TimeSpan,
    TimeUnit,
)
from cmk.rulesets.v1.form_specs.composed import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DictElement,
    Dictionary,
    List,
)
from cmk.rulesets.v1.form_specs.levels import LevelDirection, Levels
from cmk.rulesets.v1.form_specs.preconfigured import Password
from cmk.rulesets.v1.rule_specs import ActiveCheck, EvalType, Topic
from cmk.rulesets.v1.validators import DisallowEmpty


def _valuespec_response() -> Dictionary:
    return Dictionary(
        title=Localizable("Status code"),
        elements={
            "expected": DictElement(
                parameter_form=List(
                    title=Localizable("Expected"),
                    element_template=Integer(prefill=DefaultValue(200)),
                ),
                required=True,
            ),
            # TODO Not yet implemented
            # "ignored": ListOfStrings(
            #        title=Localizable("Ignored"),
            #        orientation="horizontal",
            #        default_value=["307"],
            #    ),
            # ),
        },
    )


def _valuespec_document() -> Dictionary:
    return Dictionary(
        title=Localizable("Document"),
        elements={
            "document_body": DictElement(
                parameter_form=SingleChoice(
                    title=Localizable("Document body"),
                    prefill=DefaultValue("fetch"),
                    elements=[
                        SingleChoiceElement(
                            name="fetch",
                            title=Localizable("Wait for document body"),
                        ),
                        SingleChoiceElement(
                            name="ignore",
                            title=Localizable("Get header only"),
                        ),
                    ],
                    help_text=Localizable("Note: this still does an HTTP GET or POST, not a HEAD."),
                ),
                required=True,
            ),
            "max_age": DictElement(
                # TODO How to use AGE correctly?!
                parameter_form=TimeSpan(
                    title=Localizable("Age"),
                    displayed_units=[TimeUnit.SECOND, TimeUnit.MINUTE, TimeUnit.HOUR, TimeUnit.DAY],
                    label=Localizable("Warn, if the age is older than"),
                    help_text=Localizable("Warn, if the age of the page is older than this"),
                    prefill=DefaultValue(3600 * 24),
                ),
            ),
            "page_size": DictElement(
                parameter_form=Dictionary(
                    title=Localizable("Size"),
                    elements={
                        "min": DictElement(
                            parameter_form=Integer(
                                title=Localizable("Minimum"),
                                unit=Localizable("Bytes"),
                            ),
                            required=False,
                        ),
                        "max": DictElement(
                            parameter_form=Integer(
                                title=Localizable("Maximum"),
                                unit=Localizable("Bytes"),
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
        title=Localizable("Regular expressions to expect"),
        # orientation="vertical",
        # show_titles=False,
        elements={
            # TODO Regex currently not implemented in ruleset API
            "regex": DictElement(
                parameter_form=Dictionary(
                    elements={
                        "header_name_pattern": DictElement(
                            parameter_form=Text(
                                label=Localizable("Header name pattern"),
                                # mode=RegExp.infix,
                                # maxlen=1023,
                            ),
                            required=True,
                        ),
                        "header_value_pattern": DictElement(
                            parameter_form=Text(
                                label=Localizable("Header value pattern"),
                                # mode=RegExp.infix,
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
                    label=Localizable(
                        "Case insensitive matching (only applies to header value pattern)"
                    )
                ),
                required=True,
            ),
            "invert": DictElement(
                parameter_form=BooleanChoice(
                    label=Localizable("return CRITICAL if found, OK if not")
                ),
                required=True,
            ),
        },
    )


def _valuespec_expected_regex_body() -> Dictionary:
    return Dictionary(
        title=Localizable("Regular expression to expect"),
        # orientation="vertical",
        # show_titles=False,
        elements={
            # TODO Regex currently not implemented in ruleset API
            "regex": DictElement(
                parameter_form=Text(
                    label=Localizable("Pattern"),
                    # mode=RegExp.infix,
                    # maxlen=1023,
                ),
                required=True,
            ),
            "case_insensitive": DictElement(
                parameter_form=BooleanChoice(label=Localizable("Case insensitive matching")),
                required=True,
            ),
            "multiline": DictElement(
                parameter_form=BooleanChoice(
                    label=Localizable("Line-based matching"),
                    help_text=Localizable(
                        'When checked, the anchors "^" and "$" match on every line, while '
                        '"*" doesn\'t match on newline characters'
                    ),
                ),
                required=True,
            ),
            "invert": DictElement(
                parameter_form=BooleanChoice(
                    label=Localizable("return CRITICAL if found, OK if not")
                ),
                required=True,
            ),
        },
    )


def _send_data(http_method: str | None = None) -> FixedValue | Dictionary:
    if not http_method:
        return FixedValue(
            value=None,
            label=Localizable("No additional configuration options for this method."),
        )

    return Dictionary(
        elements={
            "body_text": DictElement(
                parameter_form=Text(
                    title=Localizable("Data to send"),
                    help_text=Localizable("Please make sure, that the data is URL-encoded."),
                ),
                required=True,
            ),
            "content_type": DictElement(
                parameter_form=CascadingSingleChoice(
                    title=Localizable("Content-Type"),
                    prefill=DefaultValue("common"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="common",
                            title=Localizable("Type selection"),
                            parameter_form=SingleChoice(
                                title=Localizable("Select type from list"),
                                elements=[
                                    SingleChoiceElement(
                                        name="application_json",
                                        title=Localizable("application/json"),
                                    ),
                                    SingleChoiceElement(
                                        name="application_octet_stream",
                                        title=Localizable("application/octet-stream"),
                                    ),
                                    SingleChoiceElement(
                                        name="application_xml",
                                        title=Localizable("application/xml"),
                                    ),
                                    SingleChoiceElement(
                                        name="application_zip",
                                        title=Localizable("application/zip"),
                                    ),
                                    SingleChoiceElement(
                                        name="text_csv",
                                        title=Localizable("text/csv"),
                                    ),
                                    SingleChoiceElement(
                                        name="text_plain",
                                        title=Localizable("text/plain"),
                                    ),
                                    SingleChoiceElement(
                                        name="text_xml",
                                        title=Localizable("text/xml"),
                                    ),
                                    SingleChoiceElement(
                                        name="text_html",
                                        title=Localizable("text/html"),
                                    ),
                                ],
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="custom",
                            title=Localizable("Use custom type"),
                            parameter_form=Text(
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
    "header_name": DictElement(parameter_form=Text(label=Localizable("Name")), required=True),
    "header_value": DictElement(parameter_form=Text(label=Localizable("Value")), required=True),
}


def _valuespec_connection() -> Dictionary:
    return Dictionary(
        title=Localizable("Connection details"),
        elements={
            # Not yet implemented
            #    "virtual_host": DictElement(
            #        Text(
            #        title=Localizable("Virtual host"),
            #        size=80,
            #        input_hint="www.mydomain.de",
            #    ),
            # ),
            "http_versions": DictElement(
                parameter_form=SingleChoice(
                    title=Localizable("HTTP version"),
                    elements=[
                        SingleChoiceElement(
                            name="auto",
                            title=Localizable("Negotiate"),
                        ),
                        SingleChoiceElement(
                            name="http_2",
                            title=Localizable("Use HTTP/2"),
                        ),
                        SingleChoiceElement(name="http_1_1", title=Localizable("Use HTTP/1.1")),
                    ],
                ),
            ),
            "tls_versions": DictElement(
                parameter_form=Dictionary(
                    title=Localizable("TLS version"),
                    elements={
                        "min_version": DictElement(
                            parameter_form=SingleChoice(
                                elements=[
                                    SingleChoiceElement(
                                        name="auto", title=Localizable("Negotiate")
                                    ),
                                    SingleChoiceElement(
                                        name="tls_1_3", title=Localizable("Enforce TLS v1.3")
                                    ),
                                    SingleChoiceElement(
                                        name="tls_1_2", title=Localizable("Enforce TLS v1.2")
                                    ),
                                    SingleChoiceElement(
                                        name="tls_1_1", title=Localizable("Enforce TLS v1.1")
                                    ),
                                    SingleChoiceElement(
                                        name="tls_1_0", title=Localizable("Enforce TLS v1.0")
                                    ),
                                ],
                            ),
                            required=True,
                        ),
                        "allow_higher": DictElement(
                            parameter_form=BooleanChoice(
                                label=Localizable("Allow higher versions")
                            ),
                            required=True,
                        ),
                    },
                ),
            ),
            "method": DictElement(
                parameter_form=CascadingSingleChoice(
                    title=Localizable("HTTP method"),
                    prefill=DefaultValue("get"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="get", title=Localizable("GET"), parameter_form=_send_data("GET")
                        ),
                        CascadingSingleChoiceElement(
                            name="post",
                            title=Localizable("POST"),
                            parameter_form=_send_data("POST"),
                        ),
                        CascadingSingleChoiceElement(
                            name="put", title=Localizable("PUT"), parameter_form=_send_data("PUT")
                        ),
                        CascadingSingleChoiceElement(
                            name="delete",
                            title=Localizable("DELETE"),
                            parameter_form=_send_data("DELETE"),
                        ),
                        CascadingSingleChoiceElement(
                            name="options",
                            title=Localizable("OPTIONS"),
                            parameter_form=_send_data(),
                        ),
                        CascadingSingleChoiceElement(
                            name="trace",
                            title=Localizable("TRACE"),
                            parameter_form=_send_data(),
                        ),
                        CascadingSingleChoiceElement(
                            name="head",
                            title=Localizable("HEAD"),
                            parameter_form=_send_data(),
                        ),
                        CascadingSingleChoiceElement(
                            name="connect",
                            title=Localizable("CONNECT"),
                            parameter_form=_send_data("Connect"),
                        ),
                        CascadingSingleChoiceElement(
                            name="connect_post",
                            title=Localizable("CONNECT:POST"),
                            parameter_form=_send_data(),
                        ),
                        CascadingSingleChoiceElement(
                            name="propfind",
                            title=Localizable("PROPFIND"),
                            parameter_form=_send_data(),
                        ),
                    ],
                ),
            ),
            # Not yet implemented
            # "proxy": HTTPProxyReference())
            "redirects": DictElement(
                parameter_form=SingleChoice(
                    title=Localizable("Redirects"),
                    elements=[
                        SingleChoiceElement(
                            name="ok",
                            title=Localizable("Make check OK"),
                        ),
                        SingleChoiceElement(
                            name="warning",
                            title=Localizable("Make check WARNING"),
                        ),
                        SingleChoiceElement(
                            name="critical",
                            title=Localizable("Make check CRITICAL"),
                        ),
                        SingleChoiceElement(
                            name="follow",
                            title=Localizable("Follow the redirection"),
                        ),
                        SingleChoiceElement(
                            name="sticky",
                            title=Localizable("Follow, but stay to same IP address"),
                        ),
                        SingleChoiceElement(
                            name="stickyport",
                            title=Localizable("Follow, but stay to same IP-address and port"),
                        ),
                    ],
                    prefill=DefaultValue("follow"),
                ),
            ),
            "timeout": DictElement(
                parameter_form=Integer(
                    title=Localizable("Connection timeout"),
                    unit=Localizable("sec"),
                    prefill=DefaultValue(10),
                ),
            ),
            "user_agent": DictElement(
                parameter_form=Text(
                    title=Localizable("User Agent"),
                    prefill=DefaultValue("checkmk/check_http"),
                    help_text=Localizable('String to be sent in http header as "User Agent"'),
                ),
            ),
            "add_headers": DictElement(
                parameter_form=List(
                    title=Localizable("Additional header lines"),
                    element_template=Dictionary(elements=header_dict_elements),
                ),
            ),
            "auth": DictElement(
                parameter_form=CascadingSingleChoice(
                    title=Localizable("Authentication"),
                    prefill=DefaultValue("user_auth"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="user_auth",
                            title=Localizable("User based authentication"),
                            parameter_form=Dictionary(
                                title=Localizable("User based authentication"),
                                help_text=Localizable("Credentials for HTTP Basic Authentication"),
                                elements={
                                    "user": DictElement(
                                        parameter_form=Text(
                                            title=Localizable("Username"),
                                            custom_validate=DisallowEmpty(),
                                        ),
                                        required=True,
                                    ),
                                    "password": DictElement(
                                        parameter_form=Password(
                                            title=Localizable("Password"),
                                        ),
                                        required=True,
                                    ),
                                },
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="token_auth",
                            title=Localizable("Token based authentication"),
                            parameter_form=Dictionary(
                                title=Localizable("Token based authentication"),
                                elements={
                                    "header": DictElement(
                                        parameter_form=Text(title=Localizable("API key header")),
                                        required=True,
                                    ),
                                    "token": DictElement(
                                        parameter_form=Password(title=Localizable("API key")),
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
        title=Localizable("String validation"),
        elements={
            "header": DictElement(
                parameter_form=CascadingSingleChoice(
                    title=Localizable("Header"),
                    prefill=DefaultValue("string"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="string",
                            title=Localizable("Fixed string"),
                            parameter_form=Dictionary(
                                title=Localizable("Fixed string"),
                                elements=header_dict_elements,
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="regex",
                            title=Localizable("Regular expression"),
                            parameter_form=_valuespec_expected_regex_header(),
                        ),
                    ],
                ),
            ),
            "body": DictElement(
                parameter_form=CascadingSingleChoice(
                    title=Localizable("Body"),
                    prefill=DefaultValue("string"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="string",
                            title=Localizable("Fixed string"),
                            parameter_form=Text(title=Localizable("Fixed string")),
                        ),
                        CascadingSingleChoiceElement(
                            name="regex",
                            title=Localizable("Regular expression"),
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
            Localizable("Standard settings") if is_standard else Localizable("Individual settings")
        ),
        elements={
            "connection": DictElement(parameter_form=_valuespec_connection()),
            "response_time": DictElement(
                parameter_form=Levels(
                    title=Localizable("Response time"),
                    form_spec_template=TimeSpan(
                        displayed_units=[TimeUnit.SECOND, TimeUnit.MILLISECOND],
                    ),
                    level_direction=LevelDirection.UPPER,
                    predictive=None,
                    help_text=Localizable("Maximum time the request may take."),
                    prefill_fixed_levels=DefaultValue((0.1, 0.2)),
                ),
            ),
            "server_response": DictElement(parameter_form=_valuespec_response()),
            "cert": DictElement(
                parameter_form=CascadingSingleChoice(
                    title=Localizable("Certificate validity"),
                    prefill=DefaultValue("validate"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="validate",
                            title=Localizable("Certificate validity"),
                            parameter_form=Levels(
                                title=Localizable("Check validity"),
                                form_spec_template=Integer(unit=Localizable("days")),
                                level_direction=LevelDirection.LOWER,
                                prefill_fixed_levels=InputHint((90, 60)),
                                predictive=None,
                                help_text=Localizable(
                                    "Minimum number of days a certificate has to be valid."
                                ),
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="no_validation",
                            title=Localizable("Do not check certificate"),
                            parameter_form=FixedValue(
                                value=None,
                                title=Localizable("Do not check certificate"),
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
        title=Localizable("Endpoints"),
        custom_validate=DisallowEmpty(),
        element_template=Dictionary(
            elements={
                "service_name": DictElement(
                    parameter_form=Dictionary(
                        title=Localizable("Service description"),
                        elements={
                            "prefix": DictElement(
                                parameter_form=SingleChoice(
                                    title=Localizable("Prefix"),
                                    elements=[
                                        SingleChoiceElement(
                                            name="auto",
                                            title=Localizable("Use protocol name: HTTP(S)"),
                                        ),
                                        SingleChoiceElement(
                                            name="none",
                                            title=Localizable("Do not use a prefix"),
                                        ),
                                    ],
                                ),
                                required=True,
                            ),
                            "name": DictElement(
                                parameter_form=Text(
                                    title=Localizable("Name"),
                                    custom_validate=DisallowEmpty(),
                                    prefill=InputHint("My HTTP service"),
                                ),
                                required=True,
                            ),
                        },
                    ),
                    required=True,
                ),
                "url": DictElement(
                    parameter_form=Text(
                        title=Localizable("URL"),
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
    title=Localizable("Check HTTP web service"),
    topic=Topic.NETWORKING,
    eval_type=EvalType.MERGE,
    name="httpv2",
    parameter_form=_form_active_checks_httpv2,
)
