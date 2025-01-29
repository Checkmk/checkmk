#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import cast

from cmk.gui.form_specs.private import SingleChoiceElementExtended, SingleChoiceExtended
from cmk.gui.form_specs.vue.visitors.recomposers.unknown_form_spec import recompose
from cmk.gui.valuespec import Dictionary as ValueSpecDictionary
from cmk.gui.watolib.notification_parameter import NotificationParameter
from cmk.gui.watolib.password_store import passwordstore_choices_without_user

from cmk.rulesets.v1 import Help, Message, Title
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
from cmk.rulesets.v1.form_specs.validators import LengthInRange, MatchRegex

from ._helpers import _get_url_prefix_setting


class NotificationParameterVictorOPS(NotificationParameter):
    @property
    def ident(self) -> str:
        return "victorops"

    @property
    def spec(self) -> ValueSpecDictionary:
        # TODO needed because of mixed Form Spec and old style setup
        return cast(ValueSpecDictionary, recompose(self._form_spec()).valuespec)

    def _form_spec(self):
        return Dictionary(
            title=Title("Create notification with the following parameters"),
            elements={
                "webhook_url": DictElement(
                    required=True,
                    parameter_form=CascadingSingleChoice(
                        title=Title("Splunk On-Call REST endpoint"),
                        prefill=DefaultValue("webhook_url"),
                        help_text=Help(
                            "Learn how to setup a REST endpoint "
                            '<a href="https://help.victorops.com/knowledge-base/victorops-restendpoint-integration/" target="_blank">here</a>.'
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
                                            error_msg=Message("Please enter a valid REST endpoint"),
                                        ),
                                        MatchRegex(
                                            regex=r"^https://alert\.victorops\.com/integrations/.+",
                                            error_msg=Message(
                                                "The REST endpoint must begin with "
                                                "<tt>https://alert.victorops.com/integrations</tt>"
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
                "ignore_ssl": DictElement(
                    parameter_form=FixedValue(
                        value=True,
                        title=Title("Disable SSL certificate verification"),
                        help_text=Help(
                            "Ignore unverified HTTPS request warnings. Use with caution."
                        ),
                    ),
                ),
                "proxy_url": DictElement(parameter_form=Proxy(migrate=migrate_to_proxy)),
                "url_prefix": _get_url_prefix_setting(),
            },
        )
