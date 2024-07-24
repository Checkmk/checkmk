#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import CascadingDropdown, Dictionary, FixedValue, HTTPUrl, TextInput
from cmk.gui.wato import HTTPProxyReference, MigrateToIndividualOrStoredPassword

from ._base import NotificationParameter


class NotificationParameterSMSviaIP(NotificationParameter):
    @property
    def ident(self) -> str:
        return "sms_api"

    @property
    def spec(self):
        return Dictionary(
            title=_("Create notification with the following parameters"),
            optional_keys=["ignore_ssl"],
            elements=[
                (
                    "modem_type",
                    CascadingDropdown(
                        title=_("Modem type"),
                        help=_(
                            "Choose what modem is used. Currently supported "
                            "is only Teltonika-TRB140."
                        ),
                        choices=[
                            ("trb140", _("Teltonika-TRB140")),
                        ],
                    ),
                ),
                (
                    "url",
                    HTTPUrl(
                        title=_("Modem URL"),
                        help=_(
                            "Configure your modem URL here (e.g. https://mymodem.mydomain.example)."
                        ),
                        allow_empty=False,
                    ),
                ),
                (
                    "ignore_ssl",
                    FixedValue(
                        value=True,
                        title=_("Disable SSL certificate verification"),
                        totext=_("Disable SSL certificate verification"),
                        help=_("Ignore unverified HTTPS request warnings. Use with caution."),
                    ),
                ),
                ("proxy_url", HTTPProxyReference()),
                (
                    "username",
                    TextInput(
                        title=_("Username"),
                        help=_("The user, used for login."),
                        size=40,
                        allow_empty=False,
                    ),
                ),
                (
                    "password",
                    MigrateToIndividualOrStoredPassword(
                        title=_("Password of the user"),
                        allow_empty=False,
                    ),
                ),
                (
                    "timeout",
                    TextInput(
                        title=_("Set optional timeout for connections to the modem."),
                        help=_("Here you can configure timeout settings."),
                        default_value="10",
                    ),
                ),
            ],
        )
