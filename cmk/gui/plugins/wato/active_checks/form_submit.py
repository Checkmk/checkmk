#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any

from cmk.utils.rulesets.definition import RuleGroup

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import (
    Dictionary,
    DropdownChoice,
    Integer,
    ListOfStrings,
    NetworkPort,
    RegExp,
    TextInput,
    Transform,
    Tuple,
)
from cmk.gui.wato import RulespecGroupActiveChecks


def _transform_tuple_format(params: tuple[str, Any]) -> dict:
    if isinstance(params, tuple):
        return {
            "name": params[0],
            "url_details": params[1],
        }
    return params


def _valuespec_active_checks_form_submit() -> Transform:
    return Transform(
        valuespec=Dictionary(
            title=_("Check HTML form submit"),
            help=_(
                "Check submission of HTML forms via HTTP/HTTPS using the plug-in <tt>check_form_submit</tt> "
                "provided with Checkmk. This plug-in provides more functionality than <tt>check_http</tt>, "
                "as it automatically follows HTTP redirect, accepts and uses cookies, parses forms "
                "from the requested pages, changes vars and submits them to check the response "
                "afterwards."
            ),
            elements=[
                (
                    "name",
                    TextInput(
                        title=_("Name"),
                        help=_("The name will be used in the service name"),
                        allow_empty=False,
                    ),
                ),
                (
                    "url_details",
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
                                NetworkPort(
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
                                    allow_empty=True,
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
                ),
            ],
            optional_keys=[],
        ),
        to_valuespec=_transform_tuple_format,
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupActiveChecks,
        match_type="all",
        name=RuleGroup.ActiveChecks("form_submit"),
        valuespec=_valuespec_active_checks_form_submit,
    )
)
