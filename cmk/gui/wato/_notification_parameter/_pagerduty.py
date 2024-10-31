#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.form_specs.private import SingleChoiceElementExtended, SingleChoiceExtended
from cmk.gui.form_specs.private.dictionary_extended import DictionaryExtended
from cmk.gui.form_specs.vue.visitors.recomposers.unknown_form_spec import recompose
from cmk.gui.http import request
from cmk.gui.valuespec import Dictionary as ValueSpecDictionary
from cmk.gui.watolib.notification_parameter import NotificationParameter
from cmk.gui.watolib.password_store import passwordstore_choices_without_user

from cmk.rulesets.v1 import Help, Label, Message, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    DictElement,
    FixedValue,
    migrate_to_proxy,
    Proxy,
    String,
)
from cmk.rulesets.v1.form_specs._composed import CascadingSingleChoiceElement

from ._helpers import _get_url_prefix_setting


class NotificationParameterPagerDuty(NotificationParameter):
    @property
    def ident(self) -> str:
        return "pagerduty"

    @property
    def spec(self) -> ValueSpecDictionary:
        # TODO needed because of mixed Form Spec and old style setup
        return recompose(self._form_spec()).valuespec  # type: ignore[return-value]  # expects Valuespec[Any]

    def _form_spec(self) -> DictionaryExtended:
        # TODO register CSE specific version
        return DictionaryExtended(
            title=Title("Create notification with the following parameters"),
            # optional_keys=["ignore_ssl", "proxy_url", "url_prefix"],
            # hidden_keys=["webhook_url"],
            elements={
                "routing_key": DictElement(
                    parameter_form=CascadingSingleChoice(
                        title=Title("PagerDuty Service Integration Key"),
                        help_text=Help(
                            "After setting up a new service in PagerDuty you will receive an "
                            "Integration key associated with that service. Copy that value here."
                        ),
                        elements=[
                            CascadingSingleChoiceElement(
                                name="routing_key",
                                title=Title("Integration Key"),
                                parameter_form=String(),
                            ),
                            CascadingSingleChoiceElement(
                                title=Title("URL from password store"),
                                name="store",
                                parameter_form=SingleChoiceExtended(
                                    no_elements_text=Message(
                                        "There are no elements defined for this selection yet."
                                    ),
                                    elements=[
                                        SingleChoiceElementExtended(
                                            title=Title("%s") % title, name=ident
                                        )
                                        for ident, title in passwordstore_choices_without_user()
                                        if ident is not None
                                    ],
                                    type=str,
                                ),
                            ),
                        ],
                    ),
                ),
                "webhook_url": DictElement(
                    parameter_form=FixedValue(
                        title=Title("API endpoint from PagerDuty V2"),
                        value="https://events.pagerduty.com/v2/enqueue",
                    )
                ),
                "ignore_ssl": DictElement(
                    parameter_form=FixedValue(
                        title=Title("Disable SSL certificate verification"),
                        label=Label("Disable SSL certificate verification"),
                        value="https://events.pagerduty.com/v2/enqueue",
                        help_text=Help(
                            "Ignore unverified HTTPS request warnings. Use with caution."
                        ),
                    )
                ),
                "proxy_url": DictElement(
                    parameter_form=Proxy(
                        migrate=migrate_to_proxy,
                    ),
                ),
                "url_prefix": _get_url_prefix_setting(
                    default_value="automatic_https" if request.is_ssl_request else "automatic_http",
                ),
            },
        )
