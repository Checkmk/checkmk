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
    Alternative,
    CascadingDropdown,
    Dictionary,
    DictionaryEntry,
    DropdownChoice,
    EmailAddress,
    FixedValue,
    HTTPUrl,
    Integer,
    ListChoice,
    Password,
    TextAreaUnicode,
    TextInput,
)
from cmk.gui.wato import (
    HTTPProxyReference,
    IndividualOrStoredPassword,
    MigrateToIndividualOrStoredPassword,
)
from cmk.gui.wato._notification_parameter._helpers import get_url_prefix_specs, local_site_url
from cmk.gui.watolib.password_store import passwordstore_choices

from ._base import NotificationParameter
from ._ms_teams import NotificationParameterMsTeams
from ._opsgenie_issues import NotificationParameterOpsgenie
from ._pushover import NotificationParameterPushover
from ._registry import NotificationParameterRegistry
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
    notification_parameter_registry.register(NotificationILert)
    notification_parameter_registry.register(NotificationParameterJIRA_ISSUES)
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


class NotificationILert(NotificationParameter):
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


class NotificationParameterJIRA_ISSUES(NotificationParameter):
    @property
    def ident(self) -> str:
        return "jira_issues"

    @property
    def spec(self) -> Dictionary:
        return Dictionary(
            title=_("Create notification with the following parameters"),
            optional_keys=[
                "site_customid",
                "priority",
                "resolution",
                "host_summary",
                "service_summary",
                "ignore_ssl",
                "timeout",
                "label",
            ],
            elements=[
                (
                    "url",
                    HTTPUrl(
                        title=_("JIRA URL"),
                        help=_("Configure the JIRA URL here."),
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
                (
                    "username",
                    TextInput(
                        title=_("User Name"),
                        help=_("Configure the user name here."),
                        size=40,
                        allow_empty=False,
                    ),
                ),
                (
                    "password",
                    Password(
                        title=_("Password"),
                        help=_(
                            "You need to provide a valid password to be able to send notifications."
                        ),
                        size=40,
                        allow_empty=False,
                    ),
                ),
                (
                    "project",
                    TextInput(
                        title=_("Project ID"),
                        help=_(
                            "The numerical JIRA project ID. If not set, it will be retrieved from a "
                            "custom user attribute named <tt>jiraproject</tt>. "
                            "If that is not set, the notification will fail."
                        ),
                        size=10,
                    ),
                ),
                (
                    "issuetype",
                    TextInput(
                        title=_("Issue type ID"),
                        help=_(
                            "The numerical JIRA issue type ID. If not set, it will be retrieved from a "
                            "custom user attribute named <tt>jiraissuetype</tt>. "
                            "If that is not set, the notification will fail."
                        ),
                        size=10,
                    ),
                ),
                (
                    "host_customid",
                    TextInput(
                        title=_("Host custom field ID"),
                        help=_("The numerical JIRA custom field ID for host problems."),
                        size=10,
                    ),
                ),
                (
                    "service_customid",
                    TextInput(
                        title=_("Service custom field ID"),
                        help=_("The numerical JIRA custom field ID for service problems."),
                        size=10,
                    ),
                ),
                (
                    "site_customid",
                    TextInput(
                        title=_("Site custom field ID"),
                        help=_(
                            "The numerical ID of the JIRA custom field for sites. "
                            "Please use this option if you have multiple sites in a "
                            "distributed setup which send their notifications "
                            "to the same JIRA instance."
                        ),
                        size=10,
                    ),
                ),
                (
                    "monitoring",
                    HTTPUrl(
                        title=_("Monitoring URL"),
                        help=_(
                            "Configure the base URL for the Monitoring Web-GUI here. Include the site name. "
                            "Used for link to check_mk out of jira."
                        ),
                    ),
                ),
                (
                    "priority",
                    TextInput(
                        title=_("Priority ID"),
                        help=_(
                            "The numerical JIRA priority ID. If not set, it will be retrieved from a "
                            "custom user attribute named <tt>jirapriority</tt>. "
                            "If that is not set, the standard priority will be used."
                        ),
                        size=10,
                    ),
                ),
                (
                    "host_summary",
                    TextInput(
                        title=_("Summary for host notifications"),
                        help=_(
                            "Here you are allowed to use all macros that are defined in the "
                            "notification context."
                        ),
                        default_value="Check_MK: $HOSTNAME$ - $HOSTSHORTSTATE$",
                        size=64,
                    ),
                ),
                (
                    "service_summary",
                    TextInput(
                        title=_("Summary for service notifications"),
                        help=_(
                            "Here you are allowed to use all macros that are defined in the "
                            "notification context."
                        ),
                        default_value="Check_MK: $HOSTNAME$/$SERVICEDESC$ $SERVICESHORTSTATE$",
                        size=64,
                    ),
                ),
                (
                    "label",
                    TextInput(
                        title=_("Label"),
                        help=_(
                            "Here you can set a custom label for new issues. "
                            "If not set, 'monitoring' will be used."
                        ),
                        size=16,
                    ),
                ),
                (
                    "resolution",
                    TextInput(
                        title=_("Activate resolution with following resolution transition ID"),
                        help=_(
                            "The numerical JIRA resolution transition ID. "
                            "11 - 'To Do', 21 - 'In Progress', 31 - 'Done'"
                        ),
                        size=3,
                    ),
                ),
                (
                    "timeout",
                    TextInput(
                        title=_("Set optional timeout for connections to JIRA"),
                        help=_("Here you can configure timeout settings."),
                        default_value="10",
                    ),
                ),
            ],
        )


class NotificationParameterServiceNow(NotificationParameter):
    @property
    def ident(self) -> str:
        return "servicenow"

    @property
    def spec(self) -> Dictionary:
        return Dictionary(
            title=_("Create notification with the following parameters"),
            required_keys=["url", "username", "password", "mgmt_type"],
            elements=[
                (
                    "url",
                    HTTPUrl(
                        title=_("ServiceNow URL"),
                        help=_(
                            "Configure your ServiceNow URL here (eg. https://myservicenow.com)."
                        ),
                        allow_empty=False,
                    ),
                ),
                ("proxy_url", HTTPProxyReference()),
                (
                    "username",
                    TextInput(
                        title=_("Username"),
                        help=_(
                            "The user, used for login, has to have at least the "
                            "role 'itil' in ServiceNow."
                        ),
                        size=40,
                        allow_empty=False,
                    ),
                ),
                (
                    "password",
                    IndividualOrStoredPassword(
                        title=_("Password of the user"),
                        allow_empty=False,
                    ),
                ),
                (
                    "use_site_id",
                    Alternative(
                        title=_("Use site ID prefix"),
                        help=_(
                            "Please use this option if you have multiple "
                            "sites in a distributed setup which send their "
                            "notifications to the same ServiceNow instance. "
                            "The site ID will be used as prefix for the "
                            "problem ID on incident creation."
                        ),
                        elements=[
                            FixedValue(value=False, title=_("Deactivated"), totext=""),
                            FixedValue(value=True, title=_("Use site ID"), totext=""),
                        ],
                        default_value=False,
                    ),
                ),
                (
                    "timeout",
                    TextInput(
                        title=_("Set optional timeout for connections to ServiceNow"),
                        help=_("Here you can configure timeout settings in seconds."),
                        default_value="10",
                        size=3,
                    ),
                ),
                (
                    "mgmt_type",
                    CascadingDropdown(
                        title=_("Management type"),
                        help=_(
                            "With ServiceNow you can create different "
                            "types of management issues, currently "
                            "supported are indicents and cases."
                        ),
                        choices=[
                            ("incident", _("Incident"), self._incident_vs()),
                            ("case", _("Case"), self._case_vs()),
                        ],
                    ),
                ),
            ],
        )

    def _incident_vs(self) -> Dictionary:
        return Dictionary(
            title=_("Incident"),
            required_keys=["caller"],
            elements=[
                (
                    "caller",
                    TextInput(
                        title=_("Caller ID"),
                        help=_(
                            "Caller is the user on behalf of whom the incident is being reported "
                            "within ServiceNow. Please enter the name of the caller here. "
                            "It is recommended to use the same user as used for login. "
                            "Otherwise, your ACL rules in ServiceNow must be "
                            "adjusted, so that the user who is used for login "
                            "can create/edit/resolve incidents on behalf of the "
                            "caller. Please have a look at ServiceNow "
                            "documentation for details."
                        ),
                    ),
                ),
                ("host_short_desc", self._host_short_desc(_("incidents"))),
                ("svc_short_desc", self._svc_short_desc(_("incidents"))),
                (
                    "host_desc",
                    self._host_desc(
                        title=_("Description for host incidents"),
                        help_text=_(
                            "Text that should be set in field <tt>Description</tt> "
                            "for host notifications."
                        ),
                    ),
                ),
                (
                    "svc_desc",
                    self._svc_desc(
                        title=_("Description for service incidents"),
                        help_text=_(
                            "Text that should be set in field <tt>Description</tt> "
                            "for service notifications."
                        ),
                    ),
                ),
                (
                    "urgency",
                    DropdownChoice(
                        title=_("Urgency"),
                        help=_(
                            'See <a href="https://docs.servicenow.com/bundle/'
                            "helsinki-it-service-management/page/product/incident-management/"
                            'reference/r_PrioritizationOfIncidents.html" target="_blank">'
                            "ServiceNow Incident</a> for more information."
                        ),
                        choices=[
                            ("low", _("Low")),
                            ("medium", _("Medium")),
                            ("high", _("High")),
                        ],
                        default_value="low",
                    ),
                ),
                (
                    "impact",
                    DropdownChoice(
                        title=_("Impact"),
                        help=_(
                            'See <a href="https://docs.servicenow.com/bundle/'
                            "helsinki-it-service-management/page/product/incident-management/"
                            'reference/r_PrioritizationOfIncidents.html" target="_blank">'
                            "ServiceNow Incident</a> for more information."
                        ),
                        choices=[
                            ("low", _("Low")),
                            ("medium", _("Medium")),
                            ("high", _("High")),
                        ],
                        default_value="low",
                    ),
                ),
                (
                    "ack_state",
                    Dictionary(
                        title=_("Settings for incident state in case of acknowledgement"),
                        help=_(
                            "Here you can define the state of the incident in case of an "
                            "acknowledgement of the affected host or service problem."
                        ),
                        elements=[
                            (
                                "start",
                                Alternative(
                                    title=_("State of incident if acknowledgement is set"),
                                    help=_(
                                        "Here you can define the state of the incident in case of an "
                                        "acknowledgement of the host or service problem."
                                    ),
                                    elements=[
                                        DropdownChoice(
                                            title=_(
                                                "State of incident if acknowledgement is set (predefined)"
                                            ),
                                            help=_(
                                                "Please note that the mapping to the numeric "
                                                "ServiceNow state may be changed at your system "
                                                "and can differ from our definitions. In this case "
                                                "use the option below."
                                            ),
                                            choices=self._get_state_choices("incident"),
                                            default_value="none",
                                        ),
                                        Integer(
                                            title=_(
                                                "State of incident if acknowledgement is set (as integer)"
                                            ),
                                            minvalue=0,
                                        ),
                                    ],
                                ),
                            ),
                        ],
                    ),
                ),
                ("recovery_state", self._recovery_state_vs(_("incident"))),
                (
                    "dt_state",
                    Dictionary(
                        title=_("Settings for incident state in case of downtime"),
                        help=_(
                            "Here you can define the state of the incident in case of a "
                            "downtime of the affected host or service."
                        ),
                        elements=[
                            (
                                "start",
                                Alternative(
                                    title=_("State of incident if downtime is set"),
                                    elements=[
                                        DropdownChoice(
                                            title=_(
                                                "State of incident if downtime is set (predefined)"
                                            ),
                                            help=_(
                                                "Please note that the mapping to the numeric "
                                                "ServiceNow state may be changed at your system "
                                                "and can differ from our definitions. In this case "
                                                "use the option below."
                                            ),
                                            choices=self._get_state_choices("incident"),
                                            default_value="none",
                                        ),
                                        Integer(
                                            title=_(
                                                "State of incident if downtime is set (as integer)"
                                            ),
                                            minvalue=0,
                                        ),
                                    ],
                                ),
                            ),
                            (
                                "end",
                                Alternative(
                                    title=_("State of incident if downtime expires"),
                                    help=_(
                                        "Here you can define the state of the incident in case of an "
                                        "ending acknowledgement of the host or service problem."
                                    ),
                                    elements=[
                                        DropdownChoice(
                                            title=_(
                                                "State of incident if downtime expires (predefined)"
                                            ),
                                            help=_(
                                                "Please note that the mapping to the numeric "
                                                "ServiceNow state may be changed at your system "
                                                "and can differ from our definitions. In this case "
                                                "use the option below."
                                            ),
                                            choices=self._get_state_choices("incident"),
                                            default_value="none",
                                        ),
                                        Integer(
                                            title=_(
                                                "State of incident if downtime expires (as integer)"
                                            ),
                                            minvalue=0,
                                        ),
                                    ],
                                ),
                            ),
                        ],
                    ),
                ),
            ],
        )

    def _case_vs(self) -> Dictionary:
        return Dictionary(
            title=_("Case"),
            elements=[
                ("host_short_desc", self._host_short_desc(_("cases"))),
                ("svc_short_desc", self._svc_short_desc(_("cases"))),
                (
                    "host_desc",
                    self._host_desc(
                        title=_("Resolution notes for host cases"),
                        help_text=_(
                            "Text that should be set in field <tt>Resolution notes</tt> "
                            "on recovery service notifications."
                        ),
                    ),
                ),
                (
                    "svc_desc",
                    self._svc_desc(
                        title=_("Resolution notes for service cases"),
                        help_text=_(
                            "Text that should be set in field <tt>Resolution notes</tt> "
                            "on recovery service notifications."
                        ),
                    ),
                ),
                (
                    "priority",
                    DropdownChoice(
                        title=_("Priority"),
                        help=_(
                            "Here you can define with which priority the case should be created."
                        ),
                        choices=[
                            ("low", _("Low")),
                            ("moderate", _("Moderate")),
                            ("high", _("High")),
                            ("critical", _("Critical")),
                        ],
                        default_value="low",
                    ),
                ),
                ("recovery_state", self._recovery_state_vs(_("case"))),
            ],
        )

    def _host_desc(self, title: str, help_text: str) -> TextAreaUnicode:
        return TextAreaUnicode(
            title=title,
            help=help_text,
            rows=7,
            cols=58,
            monospaced=True,
            default_value="""Host: $HOSTNAME$
Event:    $EVENT_TXT$
Output:   $HOSTOUTPUT$
Perfdata: $HOSTPERFDATA$
$LONGHOSTOUTPUT$
""",
        )

    def _svc_desc(self, title: str, help_text: str) -> TextAreaUnicode:
        return TextAreaUnicode(
            title=title,
            help=help_text,
            rows=11,
            cols=58,
            monospaced=True,
            default_value="""Host: $HOSTNAME$
Service:  $SERVICEDESC$
Event:    $EVENT_TXT$
Output:   $SERVICEOUTPUT$
Perfdata: $SERVICEPERFDATA$
$LONGSERVICEOUTPUT$
""",
        )

    def _host_short_desc(self, issue_type: str) -> TextInput:
        return TextInput(
            title=_("Short description for host %s") % issue_type,
            help=_(
                "Text that should be set in field <tt>Short description</tt> "
                "for host notifications."
            ),
            default_value="Check_MK: $HOSTNAME$ - $HOSTSHORTSTATE$",
            size=64,
        )

    def _svc_short_desc(self, issue_type: str) -> TextInput:
        return TextInput(
            title=_("Short description for service %s") % issue_type,
            help=_(
                "Text that should be set in field <tt>Short description</tt> "
                "for service notifications."
            ),
            default_value="Check_MK: $HOSTNAME$/$SERVICEDESC$ $SERVICESHORTSTATE$",
            size=68,
        )

    def _recovery_state_vs(self, issue_type: str) -> Dictionary:
        return Dictionary(
            title=_("Settings for %s state in case of recovery") % issue_type,
            help=_(
                "Here you can define the state of the %s in case of a recovery "
                "of the affected host or service problem."
            )
            % issue_type,
            elements=[
                (
                    "start",
                    Alternative(
                        title=_("State of %s if recovery is set") % issue_type,
                        elements=[
                            DropdownChoice(
                                title=_("State of case if recovery is set (predefined)"),
                                help=_(
                                    "Please note that the mapping to the numeric "
                                    "ServiceNow state may be changed at your system "
                                    "and can differ from our definitions. In this case "
                                    "use the option below."
                                ),
                                choices=self._get_state_choices(issue_type),
                                default_value="none",
                            ),
                            Integer(
                                title=_("State of %s if recovery is set (as integer)") % issue_type,
                                minvalue=0,
                            ),
                        ],
                    ),
                ),
            ],
        )

    def _get_state_choices(self, issue_type: str) -> list[tuple[str, str]]:
        if issue_type == "incident":
            return [
                ("none", _("Don't change state")),
                ("new", _("New")),
                ("progress", _("In Progress")),
                ("hold", _("On Hold")),
                ("resolved", _("Resolved")),
                ("closed", _("Closed")),
                ("canceled", _("Canceled")),
            ]

        # Cases
        return [
            ("none", _("Don't change state")),
            ("new", _("New")),
            ("closed", _("Closed")),
            ("resolved", _("Resolved")),
            ("open", _("Open")),
            ("awaiting_info", _("Awaiting info")),
        ]
