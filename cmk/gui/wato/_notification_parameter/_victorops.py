#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import CascadingDropdown, Dictionary, DropdownChoice, FixedValue, HTTPUrl
from cmk.gui.wato import HTTPProxyReference
from cmk.gui.watolib.password_store import passwordstore_choices

from ._base import NotificationParameter
from ._helpers import get_url_prefix_specs, local_site_url


class NotificationParameterVictorOPS(NotificationParameter):
    @property
    def ident(self) -> str:
        return "victorops"

    @property
    def spec(self) -> Dictionary:
        return Dictionary(
            title=_("Create notification with the following parameters"),
            optional_keys=["ignore_ssl", "proxy_url", "url_prefix"],
            elements=[
                (
                    "webhook_url",
                    CascadingDropdown(
                        title=_("Splunk On-Call REST Endpoint"),
                        help=_(
                            "Learn how to setup a REST endpoint "
                            '<a href="https://help.victorops.com/knowledge-base/victorops-restendpoint-integration/" target="_blank">here</a>.'
                            "<br />This URL can also be collected from the password store from Checkmk."
                        ),
                        choices=[
                            (
                                "webhook_url",
                                _("REST Endpoint URL"),
                                HTTPUrl(
                                    allow_empty=False,
                                    regex=r"^https://alert\.victorops\.com/integrations/.+",
                                    regex_error=_(
                                        "The Webhook-URL must begin with "
                                        "<tt>https://alert.victorops.com/integrations</tt>"
                                    ),
                                ),
                            ),
                            (
                                "store",
                                _("URL from password store"),
                                DropdownChoice(
                                    sorted=True,
                                    choices=passwordstore_choices,
                                ),
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
                ("url_prefix", get_url_prefix_specs(local_site_url)),
            ],
        )
