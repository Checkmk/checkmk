#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import CascadingDropdown, Dictionary, DropdownChoice, FixedValue, TextInput
from cmk.gui.wato import HTTPProxyReference
from cmk.gui.watolib.password_store import passwordstore_choices

from ._base import NotificationParameter
from ._helpers import get_url_prefix_specs, local_site_url


class NotificationParameterILert(NotificationParameter):
    @property
    def ident(self) -> str:
        return "ilert"

    @property
    def spec(self) -> Dictionary:
        return Dictionary(
            title=_("Create notification with the following parameters"),
            optional_keys=["ignore_ssl", "proxy_url"],
            elements=[
                (
                    "ilert_api_key",
                    CascadingDropdown(
                        title=_("iLert alert source API key"),
                        help=_("API key for iLert alert server"),
                        choices=[
                            (
                                "ilert_api_key",
                                _("API key"),
                                TextInput(size=80, allow_empty=False),
                            ),
                            (
                                "store",
                                _("API key from password store"),
                                DropdownChoice(sorted=True, choices=passwordstore_choices),
                            ),
                        ],
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
                    "ilert_priority",
                    DropdownChoice(
                        sorted=True,
                        choices=[
                            ("HIGH", _("High (with escalation)")),
                            ("LOW", _("Low (without escalation")),
                        ],
                        title=_(
                            "Notification priority (This will override the priority configured in the alert source)"
                        ),
                        default_value="HIGH",
                    ),
                ),
                (
                    "ilert_summary_host",
                    TextInput(
                        title=_("Custom incident summary for host alerts"),
                        default_value="$NOTIFICATIONTYPE$ Host Alert: $HOSTNAME$ is $HOSTSTATE$ - $HOSTOUTPUT$",
                        size=64,
                    ),
                ),
                (
                    "ilert_summary_service",
                    TextInput(
                        title=_("Custom incident summary for service alerts"),
                        default_value="$NOTIFICATIONTYPE$ Service Alert: $HOSTALIAS$/$SERVICEDESC$ is $SERVICESTATE$ - $SERVICEOUTPUT$",
                        size=64,
                    ),
                ),
                (
                    "url_prefix",
                    get_url_prefix_specs(local_site_url, default_value="automatic_https"),
                ),
            ],
        )
