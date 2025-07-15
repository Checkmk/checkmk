#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.form_specs.private import SingleChoiceElementExtended, SingleChoiceExtended
from cmk.gui.watolib.password_store import passwordstore_choices_without_user

from cmk.rulesets.v1 import Help, Label, Message, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    migrate_to_proxy,
    Proxy,
    String,
)
from cmk.rulesets.v1.form_specs.validators import LengthInRange

from ._helpers import _get_url_prefix_setting


def form_spec() -> Dictionary:
    return Dictionary(
        title=Title("Cisco Webex Teams parameters"),
        elements={
            "webhook_url": DictElement(
                parameter_form=CascadingSingleChoice(
                    title=Title("Webhook URL"),
                    prefill=DefaultValue("webhook_url"),
                    help_text=Help(
                        "Webhook URL. Setup Cisco Webex Teams Webhook "
                        '<a href="https://apphub.webex.com/messaging/applications/incoming-webhooks-cisco-systems-38054" target="_blank">here</a>'
                        "<br />This URL can also be collected from the password "
                        "store of Checkmk."
                    ),
                    elements=[
                        CascadingSingleChoiceElement(
                            title=Title("Explicit"),
                            name="webhook_url",
                            parameter_form=String(
                                custom_validate=[
                                    LengthInRange(
                                        min_value=1,
                                        error_msg=Message("Please enter a valid Webhook URL"),
                                    )
                                ],
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            title=Title("From password store"),
                            name="store",
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
                required=True,
            ),
            "url_prefix": _get_url_prefix_setting(),
            "ignore_ssl": DictElement(
                parameter_form=FixedValue(
                    title=Title("Disable SSL certificate verification"),
                    label=Label("Disable SSL certificate verification"),
                    help_text=Help("Ignore unverified HTTPS request warnings. Use with caution."),
                    value=True,
                )
            ),
            "proxy_url": DictElement(
                parameter_form=Proxy(
                    migrate=migrate_to_proxy,
                ),
            ),
        },
    )
