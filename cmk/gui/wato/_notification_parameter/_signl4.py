#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import Dictionary, FixedValue
from cmk.gui.wato import HTTPProxyReference, MigrateToIndividualOrStoredPassword

from ._base import NotificationParameter
from ._helpers import get_url_prefix_specs, local_site_url


class NotificationParameterSIGNL4(NotificationParameter):
    @property
    def ident(self) -> str:
        return "signl4"

    @property
    def spec(self) -> Dictionary:
        return Dictionary(
            title=_("Create notification with the following parameters"),
            optional_keys=["ignore_ssl", "proxy_url"],
            elements=[
                (
                    "password",
                    MigrateToIndividualOrStoredPassword(
                        title=_("Team Secret"),
                        help=_(
                            "The team secret of your SIGNL4 team. That is the last part of "
                            "your webhook URL: https://connect.signl4.com/webhook/[TEAM_SECRET]"
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
                ("url_prefix", get_url_prefix_specs(local_site_url)),
            ],
        )
