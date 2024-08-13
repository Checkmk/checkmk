#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from urllib3.util import parse_url

from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.valuespec import CascadingDropdown, Dictionary, DropdownChoice, FixedValue, HTTPUrl
from cmk.gui.wato import HTTPProxyReference
from cmk.gui.watolib.password_store import passwordstore_choices

from ._base import NotificationParameter
from ._helpers import get_url_prefix_specs, local_site_url


def _validate_slack_uses_https(url: str, html_prefix: str) -> None:
    parsed = parse_url(url)
    if (
        isinstance(parsed.host, str)
        and parsed.host.endswith("slack.com")
        and parsed.scheme != "https"
    ):
        raise MKUserError(html_prefix, _("Slack Webhooks must use HTTPS."))


class NotificationParameterSlack(NotificationParameter):
    @property
    def ident(self) -> str:
        return "slack"

    @property
    def spec(self) -> Dictionary:
        return Dictionary(
            title=_("Create notification with the following parameters"),
            optional_keys=["ignore_ssl", "url_prefix", "proxy_url"],
            elements=[
                (
                    "webhook_url",
                    CascadingDropdown(
                        title=_("Webhook URL"),
                        help=_(
                            "Webhook URL. Setup Slack Webhook "
                            '<a href="https://my.slack.com/services/new/incoming-webhook/" target="_blank">here</a>'
                            "<br />For Mattermost follow the documentation "
                            '<a href="https://docs.mattermost.com/developer/webhooks-incoming.html" target="_blank">here</a>'
                            "<br />This URL can also be collected from the password store of Checkmk."
                        ),
                        choices=[
                            (
                                "webhook_url",
                                _("Webhook URL"),
                                HTTPUrl(
                                    size=80,
                                    allow_empty=False,
                                    validate=_validate_slack_uses_https,
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
                ("url_prefix", get_url_prefix_specs(local_site_url)),
                ("proxy_url", HTTPProxyReference()),
            ],
        )
