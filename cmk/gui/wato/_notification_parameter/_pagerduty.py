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


class NotificationParameterPagerDuty(NotificationParameter):
    @property
    def ident(self) -> str:
        return "pagerduty"

    @property
    def spec(self) -> Dictionary:
        return Dictionary(
            title=_("Create notification with the following parameters"),
            optional_keys=["ignore_ssl", "proxy_url", "url_prefix"],
            hidden_keys=["webhook_url"],
            elements=[
                (
                    "routing_key",
                    CascadingDropdown(
                        title=_("PagerDuty Service Integration Key"),
                        help=_(
                            "After setting up a new service in PagerDuty you will receive an "
                            "Integration key associated with that service. Copy that value here."
                        ),
                        choices=[
                            ("routing_key", _("Integration Key"), TextInput(size=32)),
                            (
                                "store",
                                _("Key from password store"),
                                DropdownChoice(sorted=True, choices=passwordstore_choices),
                            ),
                        ],
                    ),
                ),
                (
                    "webhook_url",
                    FixedValue(
                        value="https://events.pagerduty.com/v2/enqueue",
                        title=_("API Endpoint from PagerDuty V2"),
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
                ("url_prefix", get_url_prefix_specs(local_site_url)),
            ],
        )
