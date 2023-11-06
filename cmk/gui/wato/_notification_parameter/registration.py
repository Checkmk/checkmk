#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import socket
from collections.abc import Sequence

import cmk.utils.version as cmk_version
from cmk.utils.site import url_prefix

from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    CascadingDropdown,
    Dictionary,
    DictionaryEntry,
    DropdownChoice,
    EmailAddress,
    FixedValue,
    HTTPUrl,
    Integer,
    ListChoice,
    TextAreaUnicode,
    TextInput,
)
from cmk.gui.wato import HTTPProxyReference, MigrateToIndividualOrStoredPassword
from cmk.gui.wato._notification_parameter._helpers import get_url_prefix_specs, local_site_url
from cmk.gui.watolib.password_store import passwordstore_choices

from ._base import NotificationParameter
from ._ilert import NotificationParameterILert
from ._jira_issues import NotificationParameterJiraIssues
from ._ms_teams import NotificationParameterMsTeams
from ._opsgenie_issues import NotificationParameterOpsgenie
from ._pushover import NotificationParameterPushover
from ._registry import NotificationParameterRegistry
from ._servicenow import NotificationParameterServiceNow
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


def _vs_add_common_mail_elements(elements: Sequence[DictionaryEntry]) -> list[DictionaryEntry]:
    header: list[DictionaryEntry] = [
        (
            "from",
            Dictionary(
                title="From",
                elements=[
                    (
                        "address",
                        EmailAddress(
                            title=_("Email address"),
                            size=73,
                            allow_empty=False,
                        ),
                    ),
                    (
                        "display_name",
                        TextInput(
                            title=_("Display name"),
                            size=73,
                            allow_empty=False,
                        ),
                    ),
                ],
                help=_(
                    "The email address and visible name used in the From header "
                    "of notifications messages. If no email address is specified "
                    "the default address is <tt>OMD_SITE@FQDN</tt> is used. If the "
                    "environment variable <tt>OMD_SITE</tt> is not set it defaults "
                    "to <tt>checkmk</tt>."
                ),
            ),
        ),
        (
            "reply_to",
            Dictionary(
                title="Reply to",
                elements=[
                    (
                        "address",
                        EmailAddress(
                            title=_("Email address"),
                            size=73,
                            allow_empty=False,
                        ),
                    ),
                    (
                        "display_name",
                        TextInput(
                            title=_("Display name"),
                            size=73,
                            allow_empty=False,
                        ),
                    ),
                ],
                required_keys=["address"],
                help=_(
                    "The email address and visible name used in the Reply-To header "
                    "of notifications messages."
                ),
            ),
        ),
        (
            "host_subject",
            TextInput(
                title=_("Subject for host notifications"),
                help=_(
                    "Here you are allowed to use all macros that are defined in the "
                    "notification context."
                ),
                default_value="Check_MK: $HOSTNAME$ - $EVENT_TXT$",
                size=76,
            ),
        ),
        (
            "service_subject",
            TextInput(
                title=_("Subject for service notifications"),
                help=_(
                    "Here you are allowed to use all macros that are defined in the "
                    "notification context."
                ),
                default_value="Check_MK: $HOSTNAME$/$SERVICEDESC$ $EVENT_TXT$",
                size=76,
            ),
        ),
    ]

    footer: list[DictionaryEntry] = [
        (
            "bulk_sort_order",
            DropdownChoice(
                choices=[
                    ("oldest_first", _("Oldest first")),
                    ("newest_first", _("Newest first")),
                ],
                help=_(
                    "With this option you can specify, whether the oldest (default) or "
                    "the newest notification should get shown at the top of the notification mail."
                ),
                title=_("Notification sort order for bulk notifications"),
                default_value="oldest_first",
            ),
        ),
        (
            "disable_multiplexing",
            FixedValue(
                value=True,
                title=_("Send seperate notifications to every recipient"),
                totext=_(
                    "A seperate notification is send to every recipient. Recipients "
                    "cannot see which other recipients were notified."
                ),
                help=_(
                    "Per default only one notification is generated for all recipients. "
                    "Therefore, all recipients can see who was notified and reply to "
                    "all other recipients."
                ),
            ),
        ),
    ]

    return header + list(elements) + footer


class NotificationParameterMail(NotificationParameter):
    @property
    def ident(self) -> str:
        return "mail"

    @property
    def spec(self) -> Dictionary:
        return Dictionary(
            title=_("Create notification with the following parameters"),
            # must be called at run time!!
            elements=self._parameter_elements,
        )

    def _parameter_elements(self) -> list[DictionaryEntry]:
        elements = _vs_add_common_mail_elements(
            [
                (
                    "elements",
                    ListChoice(
                        title=_("Display additional information"),
                        choices=[
                            ("omdsite", _("Site ID")),
                            ("hosttags", _("Tags of the Host")),
                            ("address", _("IP Address of Host")),
                            ("abstime", _("Absolute Time of Alert")),
                            ("reltime", _("Relative Time of Alert")),
                            ("longoutput", _("Additional Plugin Output")),
                            ("ack_author", _("Acknowledgement Author")),
                            ("ack_comment", _("Acknowledgement Comment")),
                            ("notification_author", _("Notification Author")),
                            ("notification_comment", _("Notification Comment")),
                            ("perfdata", _("Metrics")),
                            ("graph", _("Time series graph")),
                            ("notesurl", _("Custom Host/Service Notes URL")),
                            ("context", _("Complete variable list (for testing)")),
                        ],
                        default_value=["graph", "abstime", "address", "longoutput"],
                    ),
                ),
                (
                    "insert_html_section",
                    TextAreaUnicode(
                        title=_("Add HTML section above table (e.g. title, description…)"),
                        default_value="<HTMLTAG>CONTENT</HTMLTAG>",
                        cols=76,
                        rows=3,
                    ),
                ),
                (
                    "url_prefix",
                    get_url_prefix_specs(
                        "http://" + socket.gethostname() + url_prefix() + "check_mk/",
                        request.is_ssl_request and "automatic_https" or "automatic_http",
                    ),
                ),
                (
                    "no_floating_graphs",
                    FixedValue(
                        value=True,
                        title=_("Display graphs among each other"),
                        totext=_("Graphs are shown among each other"),
                        help=_(
                            "By default all multiple graphs in emails are displayed floating "
                            "nearby. You can enable this option to show the graphs among each "
                            "other."
                        ),
                    ),
                ),
                (
                    "graphs_per_notification",
                    Integer(
                        title=_("Graphs per notification (default: 5)"),
                        label=_("Show up to"),
                        unit=_("graphs"),
                        help=_(
                            "Sets a limit for the number of graphs that are displayed in a notification."
                        ),
                        default_value=5,
                        minvalue=0,
                    ),
                ),
                (
                    "notifications_with_graphs",
                    Integer(
                        title=_("Bulk notifications with graphs (default: 5)"),
                        label=_("Show graphs for the first"),
                        unit=_("Notifications"),
                        help=_(
                            "Sets a limit for the number of notifications in a bulk for which graphs "
                            "are displayed. If you do not use bulk notifications this option is ignored. "
                            "Note that each graph increases the size of the mail and takes time to render"
                            "on the monitoring server. Therefore, large bulks may exceed the maximum "
                            "size for attachements or the plugin may run into a timeout so that a failed "
                            "notification is produced."
                        ),
                        default_value=5,
                        minvalue=0,
                    ),
                ),
            ]
        )

        if cmk_version.edition() is not cmk_version.Edition.CRE:
            # Will be cleaned up soon
            import cmk.gui.cee.plugins.wato.syncsmtp  # pylint: disable=no-name-in-module,cmk-module-layer-violation

            elements += cmk.gui.cee.plugins.wato.syncsmtp.cee_html_mail_smtp_sync_option

        return elements


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
                            "After setting up a new Service in PagerDuty you will receive an "
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


class NotificationParameterASCIIMail(NotificationParameter):
    @property
    def ident(self) -> str:
        return "asciimail"

    @property
    def spec(self) -> Dictionary:
        elements = _vs_add_common_mail_elements(
            [
                (
                    "common_body",
                    TextAreaUnicode(
                        title=_("Body head for both host and service notifications"),
                        rows=7,
                        cols=58,
                        monospaced=True,
                        default_value="""Host:     $HOSTNAME$
Alias:    $HOSTALIAS$
Address:  $HOSTADDRESS$
""",
                    ),
                ),
                (
                    "host_body",
                    TextAreaUnicode(
                        title=_("Body tail for host notifications"),
                        rows=9,
                        cols=58,
                        monospaced=True,
                        default_value="""Event:    $EVENT_TXT$
Output:   $HOSTOUTPUT$
Perfdata: $HOSTPERFDATA$
$LONGHOSTOUTPUT$
""",
                    ),
                ),
                (
                    "service_body",
                    TextAreaUnicode(
                        title=_("Body tail for service notifications"),
                        rows=11,
                        cols=58,
                        monospaced=True,
                        default_value="""Service:  $SERVICEDESC$
Event:    $EVENT_TXT$
Output:   $SERVICEOUTPUT$
Perfdata: $SERVICEPERFDATA$
$LONGSERVICEOUTPUT$
""",
                    ),
                ),
            ]
        )
        return Dictionary(
            title=_("Create notification with the following parameters"), elements=elements
        )
