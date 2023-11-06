#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import CascadingDropdown, Dictionary, DropdownChoice, FixedValue, HTTPUrl
from cmk.gui.wato import HTTPProxyReference
from cmk.gui.wato._notification_parameter._helpers import get_url_prefix_specs, local_site_url
from cmk.gui.watolib.password_store import passwordstore_choices

from ._base import NotificationParameter
from ._ilert import NotificationParameterILert
from ._jira_issues import NotificationParameterJiraIssues
from ._mail import NotificationParameterASCIIMail, NotificationParameterMail
from ._ms_teams import NotificationParameterMsTeams
from ._opsgenie_issues import NotificationParameterOpsgenie
from ._pagerduty import NotificationParameterPagerDuty
from ._pushover import NotificationParameterPushover
from ._registry import NotificationParameterRegistry
from ._servicenow import NotificationParameterServiceNow
from ._signl4 import NotificationParameterSIGNL4
from ._sms_api import NotificationParameterSMSviaIP
from ._spectrum import NotificationParameterSpectrum


def register(notification_parameter_registry: NotificationParameterRegistry) -> None:
    notification_parameter_registry.register(NotificationParameterMail)
    notification_parameter_registry.register(NotificationParameterSlack)
    notification_parameter_registry.register(NotificationParameterCiscoWebexTeams)
    notification_parameter_registry.register(NotificationParameterVictorOPS)
    notification_parameter_registry.register(NotificationParameterPagerDuty)
    notification_parameter_registry.register(NotificationParameterSIGNL4)
    notification_parameter_registry.register(NotificationParameterASCIIMail)
    notification_parameter_registry.register(NotificationParameterILert)
    notification_parameter_registry.register(NotificationParameterJiraIssues)
    notification_parameter_registry.register(NotificationParameterServiceNow)
    notification_parameter_registry.register(NotificationParameterOpsgenie)
    notification_parameter_registry.register(NotificationParameterSpectrum)
    notification_parameter_registry.register(NotificationParameterPushover)
    notification_parameter_registry.register(NotificationParameterSMSviaIP)
    notification_parameter_registry.register(NotificationParameterMsTeams)


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
                        title=_("Webhook-URL"),
                        help=_(
                            "Webhook URL. Setup Slack Webhook "
                            '<a href="https://my.slack.com/services/new/incoming-webhook/" target="_blank">here</a>'
                            "<br />For Mattermost follow the documentation "
                            '<a href="https://docs.mattermost.com/developer/webhooks-incoming.html" target="_blank">here</a>'
                            "<br />This URL can also be collected from the Password Store from Checkmk."
                        ),
                        choices=[
                            (
                                "webhook_url",
                                _("Webhook URL"),
                                HTTPUrl(size=80, allow_empty=False),
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


class NotificationParameterCiscoWebexTeams(NotificationParameter):
    @property
    def ident(self) -> str:
        return "cisco_webex_teams"

    @property
    def spec(self) -> Dictionary:
        return Dictionary(
            title=_("Create notification with the following parameters"),
            optional_keys=["ignore_ssl", "url_prefix", "proxy_url"],
            elements=[
                (
                    "webhook_url",
                    CascadingDropdown(
                        title=_("Webhook-URL"),
                        help=_(
                            "Webhook URL. Setup Cisco Webex Teams Webhook "
                            '<a href="https://apphub.webex.com/messaging/applications/incoming-webhooks-cisco-systems-38054" target="_blank">here</a>'
                            "<br />This URL can also be collected from the Password Store from Checkmk."
                        ),
                        choices=[
                            ("webhook_url", _("Webhook URL"), HTTPUrl(size=80, allow_empty=False)),
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
                ("url_prefix", get_url_prefix_specs(local_site_url)),
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
            ],
        )


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
                            '<a href="https://help.victorops.com/knowledge-base/victorops-restendpoint-integration/" target="_blank">here</a>'
                            "<br />This URL can also be collected from the Password Store from Checkmk."
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
