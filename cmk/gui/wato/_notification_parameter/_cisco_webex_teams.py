#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.form_specs.private import SingleChoiceElementExtended, SingleChoiceExtended
from cmk.gui.form_specs.vue.visitors.recomposers.unknown_form_spec import recompose
from cmk.gui.valuespec import Dictionary as ValueSpecDictionary
from cmk.gui.watolib.notification_parameter import NotificationParameter
from cmk.gui.watolib.password_store import passwordstore_choices_without_user

from cmk.rulesets.v1 import Help, Label, Message, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DictElement,
    Dictionary,
    FixedValue,
    migrate_to_proxy,
    Proxy,
    String,
)

from ._helpers import _get_url_prefix_setting


class NotificationParameterCiscoWebexTeams(NotificationParameter):
    @property
    def ident(self) -> str:
        return "cisco_webex_teams"

    @property
    def spec(self) -> ValueSpecDictionary:
        # TODO needed because of mixed Form Spec and old style setup
        return recompose(self._form_spec()).valuespec  # type: ignore[return-value]  # expects Valuespec[Any]

    def _form_spec(self) -> Dictionary:
        return Dictionary(
            title=Title("Create notification with the following parameters"),
            elements={
                "webhook_url": DictElement(
                    parameter_form=CascadingSingleChoice(
                        title=Title("Webhook-URL"),
                        help_text=Help(
                            "Webhook URL. Setup Cisco Webex Teams Webhook "
                            '<a href="https://apphub.webex.com/messaging/applications/incoming-webhooks-cisco-systems-38054" target="_blank">here</a>'
                            "<br />This URL can also be collected from the password "
                            "store of Checkmk."
                        ),
                        elements=[
                            CascadingSingleChoiceElement(
                                title=Title("Webhook URL"),
                                name="webhook_url",
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
                    required=True,
                ),
                "url_prefix": _get_url_prefix_setting(),
                "ignore_ssl": DictElement(
                    parameter_form=FixedValue(
                        title=Title("Disable SSL certificate verification"),
                        label=Label("Disable SSL certificate verification"),
                        help_text=Help(
                            "Ignore unverified HTTPS request warnings. Use with caution."
                        ),
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
