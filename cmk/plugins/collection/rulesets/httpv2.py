#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Localizable
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DictElement,
    Dictionary,
    FixedLevels,
    FixedValue,
    Float,
    Integer,
    LevelDirection,
    Levels,
    List,
    SingleChoice,
    SingleChoiceElement,
    Text,
    TimeSpan,
    TupleDoNotUseWillbeRemoved,
)
from cmk.rulesets.v1.preconfigured import Password
from cmk.rulesets.v1.rule_specs import ActiveChecks, EvalType, Topic
from cmk.rulesets.v1.validators import DisallowEmpty


def _valuespec_response() -> Dictionary:
    return Dictionary(
        title=Localizable("Status code"),
        elements={
            "expected": DictElement(
                List(
                    title=Localizable("Expected"),
                    parameter_form=Integer(prefill_value=200),
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
                SingleChoice(
                    title=Localizable("Document body"),
                    prefill_selection="fetch",
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
                TimeSpan(
                    title=Localizable("Age"),
                    label=Localizable("Warn, if the age is older than"),
                    help_text=Localizable("Warn, if the age of the page is older than this"),
                    prefill_value=3600 * 24,
                ),
            ),
            "page_size": DictElement(
                TupleDoNotUseWillbeRemoved(
                    title=Localizable("Size"),
                    elements=[
                        Integer(
                            title=Localizable("Minimum"),
                            unit=Localizable("Bytes"),
                        ),
                        Integer(
                            title=Localizable("Maximum"),
                            unit=Localizable("Bytes"),
                        ),
                    ],
                ),
            ),
        },
    )


def _valuespec_expected_regex() -> TupleDoNotUseWillbeRemoved:
    return TupleDoNotUseWillbeRemoved(
        title=Localizable("Regular expression to expect"),
        # orientation="vertical",
        # show_titles=False,
        elements=[
            # TODO Regex currently not implemented in ruleset API
            TupleDoNotUseWillbeRemoved(
                elements=[
                    TupleDoNotUseWillbeRemoved(
                        elements=[
                            Text(
                                label=Localizable("Name"),
                                # mode=RegExp.infix,
                                # maxlen=1023,
                            ),
                            Text(
                                label=Localizable("Value"),
                                # mode=RegExp.infix,
                                # maxlen=1023,
                            ),
                        ],
                    ),
                ]
            ),
            BooleanChoice(label=Localizable("Case insensitive (only applies to header value)")),
            BooleanChoice(label=Localizable("return CRITICAL if found, OK if not")),
        ],
    )


def _send_data(http_method: str | None = None) -> FixedValue | TupleDoNotUseWillbeRemoved:
    if not http_method:
        return FixedValue(
            value=None,
            label=Localizable("No additional configuration options for this method."),
        )

    return TupleDoNotUseWillbeRemoved(
        elements=[
            Text(
                title=Localizable("Data to send"),
                help_text=Localizable("Please make sure, that the data is URL-encoded."),
            ),
            CascadingSingleChoice(
                title=Localizable("Content-Type"),
                prefill_selection="common",
                elements=[
                    CascadingSingleChoiceElement(
                        name="common",
                        title=Localizable("Type selection"),
                        parameter_form=SingleChoice(
                            title=Localizable("Select type from list"),
                            elements=[
                                SingleChoiceElement(
                                    name="application/json",
                                    title=Localizable("application/json"),
                                ),
                                SingleChoiceElement(
                                    name="application/octet-stream",
                                    title=Localizable("application/octet-stream"),
                                ),
                                SingleChoiceElement(
                                    name="application/xml",
                                    title=Localizable("application/xml"),
                                ),
                                SingleChoiceElement(
                                    name="application/zip",
                                    title=Localizable("application/zip"),
                                ),
                                SingleChoiceElement(
                                    name="text/csv",
                                    title=Localizable("text/csv"),
                                ),
                                SingleChoiceElement(
                                    name="text/plain",
                                    title=Localizable("text/plain"),
                                ),
                                SingleChoiceElement(
                                    name="text/xml",
                                    title=Localizable("text/xml"),
                                ),
                                SingleChoiceElement(
                                    name="text/html",
                                    title=Localizable("text/html"),
                                ),
                            ],
                        ),
                    ),
                    CascadingSingleChoiceElement(
                        name="custom",
                        title=Localizable("Use custom type"),
                        parameter_form=Text(
                            input_hint="text/plain",
                        ),
                    ),
                ],
            ),
        ],
    )


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
                SingleChoice(
                    title=Localizable("HTTP version"),
                    elements=[
                        SingleChoiceElement(
                            name="auto",
                            title=Localizable("Negotiate"),
                        ),
                        SingleChoiceElement(
                            name="http2",
                            title=Localizable("Use HTTP/2"),
                        ),
                        SingleChoiceElement(
                            name="http11",
                            title=Localizable("Use HTTP/1.1"),
                        ),
                        SingleChoiceElement(
                            name="http10",
                            title=Localizable("Use HTTP/1.0"),
                        ),
                    ],
                ),
            ),
            "tls_versions": DictElement(
                TupleDoNotUseWillbeRemoved(
                    title=Localizable("SSL version"),
                    elements=[
                        SingleChoice(
                            elements=[
                                SingleChoiceElement(name="auto", title=Localizable("Negotiate")),
                                SingleChoiceElement(
                                    name="1.3", title=Localizable("Enforce TLS v1.3")
                                ),
                                SingleChoiceElement(
                                    name="1.2", title=Localizable("Enforce TLS v1.2")
                                ),
                                SingleChoiceElement(
                                    name="1.1", title=Localizable("Enforce TLS v1.1")
                                ),
                                SingleChoiceElement(
                                    name="1", title=Localizable("Enforce TLS v1.0")
                                ),
                            ],
                        ),
                        BooleanChoice(label=Localizable("Allow higher versions")),
                    ],
                ),
            ),
            "method": DictElement(
                CascadingSingleChoice(
                    title=Localizable("HTTP method"),
                    prefill_selection="GET",
                    elements=[
                        CascadingSingleChoiceElement(
                            name="GET", title=Localizable("GET"), parameter_form=_send_data("GET")
                        ),
                        CascadingSingleChoiceElement(
                            name="POST",
                            title=Localizable("POST"),
                            parameter_form=_send_data("POST"),
                        ),
                        CascadingSingleChoiceElement(
                            name="PUT", title=Localizable("PUT"), parameter_form=_send_data("PUT")
                        ),
                        CascadingSingleChoiceElement(
                            name="DELETE",
                            title=Localizable("DELETE"),
                            parameter_form=_send_data("DELETE"),
                        ),
                        CascadingSingleChoiceElement(
                            name="OPTIONS",
                            title=Localizable("OPTIONS"),
                            parameter_form=_send_data(),
                        ),
                        CascadingSingleChoiceElement(
                            name="TRACE",
                            title=Localizable("TRACE"),
                            parameter_form=_send_data(),
                        ),
                        CascadingSingleChoiceElement(
                            name="HEAD",
                            title=Localizable("HEAD"),
                            parameter_form=_send_data(),
                        ),
                        CascadingSingleChoiceElement(
                            name="CONNECT",
                            title=Localizable("CONNECT"),
                            parameter_form=_send_data("Connect"),
                        ),
                        CascadingSingleChoiceElement(
                            name="CONNECT:POST",
                            title=Localizable("CONNECT:POST"),
                            parameter_form=_send_data(),
                        ),
                        CascadingSingleChoiceElement(
                            name="PROPFIND",
                            title=Localizable("PROPFIND"),
                            parameter_form=_send_data(),
                        ),
                    ],
                ),
            ),
            # Not yet implemented
            # "proxy": HTTPProxyReference())
            "redirects": DictElement(
                SingleChoice(
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
                    prefill_selection="follow",
                ),
            ),
            "timeout": DictElement(
                Integer(
                    title=Localizable("Connection timeout"),
                    unit=Localizable("sec"),
                    prefill_value=10,
                ),
            ),
            "user_agent": DictElement(
                Text(
                    title=Localizable("User Agent"),
                    prefill_value="checkmk",
                    help_text=Localizable('String to be sent in http header as "User Agent"'),
                ),
            ),
            "add_headers": DictElement(
                List(
                    title=Localizable("Additional header lines"),
                    parameter_form=TupleDoNotUseWillbeRemoved(
                        elements=[
                            Text(label=Localizable("Name")),
                            Text(label=Localizable("Value")),
                        ]
                    ),
                ),
            ),
            "auth": DictElement(
                CascadingSingleChoice(
                    title=Localizable("Authentication"),
                    prefill_selection="user_auth",
                    elements=[
                        CascadingSingleChoiceElement(
                            name="user_auth",
                            title=Localizable("User based authentication"),
                            parameter_form=TupleDoNotUseWillbeRemoved(
                                title=Localizable("User based authentication"),
                                help_text=Localizable("Credentials for HTTP Basic Authentication"),
                                elements=[
                                    Text(
                                        title=Localizable("Username"),
                                        custom_validate=DisallowEmpty(),
                                    ),
                                    Password(
                                        title=Localizable("Password"),
                                    ),
                                ],
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="token_auth",
                            title=Localizable("Token based authentication"),
                            parameter_form=TupleDoNotUseWillbeRemoved(
                                title=Localizable("Token based authentication"),
                                elements=[
                                    Text(title=Localizable("API key header")),
                                    Password(title=Localizable("API key")),
                                ],
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
                CascadingSingleChoice(
                    title=Localizable("Header"),
                    prefill_selection="string",
                    elements=[
                        CascadingSingleChoiceElement(
                            name="string",
                            title=Localizable("Fixed string"),
                            parameter_form=TupleDoNotUseWillbeRemoved(
                                title=Localizable("Fixed string"),
                                elements=[
                                    Text(label=Localizable("Name")),
                                    Text(label=Localizable("Value")),
                                ],
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="regex",
                            title=Localizable("Regular expression"),
                            parameter_form=_valuespec_expected_regex(),
                        ),
                    ],
                ),
            ),
            "body": DictElement(
                CascadingSingleChoice(
                    title=Localizable("Body"),
                    prefill_selection="string",
                    elements=[
                        CascadingSingleChoiceElement(
                            name="string",
                            title=Localizable("Fixed string"),
                            parameter_form=Text(Localizable("Fixed string")),
                        ),
                        CascadingSingleChoiceElement(
                            name="regex",
                            title=Localizable("Regular expression"),
                            parameter_form=_valuespec_expected_regex(),
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
        title=Localizable("Standard settings")
        if is_standard
        else Localizable("Individual settings"),
        elements={
            "connection": DictElement(_valuespec_connection()),
            "response_time": DictElement(
                TupleDoNotUseWillbeRemoved(
                    title=Localizable("Response time"),
                    elements=[
                        # TODO this should be ms but only seconds are supported
                        # by the API right now
                        Float(
                            title=Localizable("Warning if above"),
                            unit=Localizable("s"),
                            prefill_value=0.1,
                        ),
                        Float(
                            title=Localizable("Critical if above"),
                            unit=Localizable("s"),
                            prefill_value=0.2,
                        ),
                    ],
                )
            ),
            "server_response": DictElement(_valuespec_response()),
            "cert": DictElement(
                CascadingSingleChoice(
                    title=Localizable("Certificate validity"),
                    prefill_selection="validate",
                    elements=[
                        CascadingSingleChoiceElement(
                            name="validate",
                            title=Localizable("Certificate validity"),
                            parameter_form=Levels(
                                title=Localizable("Check validity"),
                                form_spec=Integer,
                                fixed=FixedLevels(),
                                level_direction=LevelDirection.LOWER,
                                predictive=None,
                                unit=Localizable("days"),
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
            "document": DictElement(_valuespec_document()),
            "content": DictElement(_valuespec_content()),
        },
    )


def _valuespec_endpoints() -> List:
    return List(
        title=Localizable("Endpoints"),
        custom_validate=DisallowEmpty(),
        parameter_form=Dictionary(
            elements={
                "service_name": DictElement(
                    TupleDoNotUseWillbeRemoved(
                        title=Localizable("Service description"),
                        elements=[
                            SingleChoice(
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
                            Text(
                                title=Localizable("Suffix"),
                                custom_validate=DisallowEmpty(),
                                input_hint="Name to be used for the Checkmk service",
                            ),
                        ],
                    ),
                    required=True,
                ),
                "url": DictElement(
                    Text(
                        title=Localizable("URL"),
                        input_hint="https://subdomain.domain.tld:port/path/to/filename",
                    ),
                    required=True,
                ),
                "individual_settings": DictElement(_valuespec_settings(is_standard=False)),
            },
        ),
    )


def _form_active_checks_httpv2() -> Dictionary:
    return Dictionary(
        elements={
            "endpoints": DictElement(_valuespec_endpoints(), required=True),
            "standard_settings": DictElement(_valuespec_settings()),
        },
    )


rule_spec_httpv2 = ActiveChecks(
    title=Localizable("Check HTTP web service"),
    topic=Topic.NETWORKING,
    eval_type=EvalType.MERGE,
    name="httpv2",
    parameter_form=_form_active_checks_httpv2,
)
