#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.watolib.password_store import passwordstore_choices_without_user
from cmk.rulesets.internal.form_specs import SingleChoiceElementExtended, SingleChoiceExtended
from cmk.rulesets.v1 import Help, Label, Message, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    migrate_to_password,
    migrate_to_proxy,
    Password,
    Proxy,
    String,
)
from cmk.rulesets.v1.form_specs.validators import LengthInRange, MatchRegex

from ._helpers import _get_url_prefix_setting


def form_spec() -> Dictionary:
    return Dictionary(
        title=Title("Flowtriq parameters"),
        elements={
            "webhook_url": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    title=Title("Flowtriq webhook URL"),
                    prefill=DefaultValue("webhook_url"),
                    help_text=Help(
                        "The URL of your Flowtriq webhook endpoint. "
                        "Alerts will be sent as JSON POST requests to this URL."
                        "<br />This URL can also be collected from the password store of Checkmk."
                    ),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="webhook_url",
                            title=Title("Explicit"),
                            parameter_form=String(
                                custom_validate=[
                                    LengthInRange(
                                        min_value=1,
                                        error_msg=Message(
                                            "Please enter a valid webhook URL"
                                        ),
                                    ),
                                    MatchRegex(
                                        regex=r"^https?://.+",
                                        error_msg=Message(
                                            "The webhook URL must begin with "
                                            "<tt>https://</tt> or <tt>http://</tt>"
                                        ),
                                    ),
                                ],
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="store",
                            title=Title("From password store"),
                            parameter_form=SingleChoiceExtended(
                                no_elements_text=Message(
                                    "There are no passwords defined for this selection yet."
                                ),
                                elements=[
                                    SingleChoiceElementExtended(
                                        title=Title("%s") % title, name=ident
                                    )
                                    for ident, title in passwordstore_choices_without_user()
                                    if ident is not None
                                ],
                            ),
                        ),
                    ],
                ),
            ),
            "api_key": DictElement(
                parameter_form=Password(
                    title=Title("API Key"),
                    help_text=Help(
                        "An optional API key for authenticating with the Flowtriq webhook. "
                        "If set, it will be sent as an <tt>X-API-Key</tt> HTTP header."
                    ),
                    migrate=migrate_to_password,
                ),
            ),
            "ignore_ssl": DictElement(
                parameter_form=FixedValue(
                    value=True,
                    title=Title("Disable SSL certificate verification"),
                    label=Label("Disable SSL certificate verification"),
                    help_text=Help(
                        "Ignore unverified HTTPS request warnings. Use with caution."
                    ),
                ),
            ),
            "proxy_url": DictElement(parameter_form=Proxy(migrate=migrate_to_proxy)),
            "url_prefix": _get_url_prefix_setting(),
        },
    )
