#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import socket

import cmk
import cmk.gui.mkeventd as mkeventd
import cmk.gui.config as config
from cmk.gui.i18n import _
from cmk.gui.globals import html

from cmk.gui.valuespec import (
    Age,
    CascadingDropdown,
    Dictionary,
    DropdownChoice,
    EmailAddress,
    FixedValue,
    HTTPUrl,
    IPv4Address,
    ListChoice,
    ListOfStrings,
    Password,
    TextAreaUnicode,
    TextAscii,
    TextUnicode,
    Transform,
    Tuple,
)

from cmk.gui.plugins.wato import (
    notification_parameter_registry,
    NotificationParameter,
    passwordstore_choices,
    HTTPProxyReference,
)

from cmk.gui.plugins.wato.utils import (
    PasswordFromStore,)


# We have to transform because 'add_to_event_context'
# in modules/events.py can't handle complex data structures
def transform_back_html_mail_url_prefix(p):
    if isinstance(p, tuple):
        return {p[0]: p[1]}
    if p == "automatic_http":
        return {"automatic": "http"}
    if p == "automatic_https":
        return {"automatic": "https"}
    return {"manual": p}


def transform_forth_html_mail_url_prefix(p):
    if not isinstance(p, dict):
        return ("manual", p)

    k, v = p.items()[0]
    if k == "automatic":
        return "%s_%s" % (k, v)

    return ("manual", v)


def local_site_url():
    return "http://" + socket.gethostname() + "/" + config.omd_site() + "check_mk/",


@notification_parameter_registry.register
class NotificationParameterMail(NotificationParameter):
    @property
    def ident(self):
        return "mail"

    @property
    def spec(self):
        return Dictionary(
            # must be called at run time!!
            elements=self._parameter_elements,)

    def _parameter_elements(self):
        elements = [
            ("from", EmailAddress(
                title=_("From: Address"),
                size=40,
                allow_empty=False,
            )),
            ("reply_to", EmailAddress(
                title=_("Reply-To: Address"),
                size=40,
                allow_empty=False,
            )),
            ("host_subject",
             TextUnicode(
                 title=_("Subject for host notifications"),
                 help=_("Here you are allowed to use all macros that are defined in the "
                        "notification context."),
                 default_value="Check_MK: $HOSTNAME$ - $EVENT_TXT$",
                 size=64,
             )),
            ("service_subject",
             TextUnicode(
                 title=_("Subject for service notifications"),
                 help=_("Here you are allowed to use all macros that are defined in the "
                        "notification context."),
                 default_value="Check_MK: $HOSTNAME$/$SERVICEDESC$ $EVENT_TXT$",
                 size=64,
             )),
            ("elements",
             ListChoice(
                 title=_("Information to be displayed in the email body"),
                 choices=[
                     ("omdsite", _("OMD Site")),
                     ("hosttags", _("Tags of the Host")),
                     ("address", _("IP Address of Host")),
                     ("abstime", _("Absolute Time of Alert")),
                     ("reltime", _("Relative Time of Alert")),
                     ("longoutput", _("Additional Plugin Output")),
                     ("ack_author", _("Acknowledgement Author")),
                     ("ack_comment", _("Acknowledgement Comment")),
                     ("perfdata", _("Performance Data")),
                     ("graph", _("Performance Graphs")),
                     ("notesurl", _("Custom Host/Service Notes URL")),
                     ("context", _("Complete variable list (for testing)")),
                 ],
                 default_value=["perfdata", "graph", "abstime", "address", "longoutput"],
             )),
            ("insert_html_section",
             TextAreaUnicode(
                 title=_("Insert HTML section between body and table"),
                 default_value="<HTMLTAG>CONTENT</HTMLTAG>",
                 cols=40,
                 rows="auto",
             )),
            ("url_prefix",
             Transform(CascadingDropdown(
                 style="dropdown",
                 title=_("URL prefix for links to Check_MK"),
                 help=_("If you use <b>Automatic HTTP/s</b> the URL prefix for "
                        "host and service links within the notification mail "
                        "is filled automatically. "
                        "If you specify an URL prefix here, then several parts of the "
                        "email body are armed with hyperlinks to your Check_MK GUI. In both cases "
                        "the recipient of the email can directly visit the host or "
                        "service in question in Check_MK. Specify an absolute URL including "
                        "the <tt>.../check_mk/</tt>"),
                 choices=[
                     ("automatic_http", _("Automatic HTTP")),
                     ("automatic_https", _("Automatic HTTPs")),
                     ("manual", _("Specify URL prefix"),
                      TextAscii(
                          regex="^(http|https)://.*/check_mk/$",
                          regex_error=_("The URL must begin with <tt>http</tt> or "
                                        "<tt>https</tt> and end with <tt>/check_mk/</tt>."),
                          size=64,
                          default_value="http://" + socket.gethostname() + "/" +
                          (config.omd_site() and config.omd_site() + "/" or "") + "check_mk/",
                      )),
                 ],
                 default_value=html.request.is_ssl_request and "automatic_https" or
                 "automatic_http",
             ),
                       forth=transform_forth_html_mail_url_prefix,
                       back=transform_back_html_mail_url_prefix)),
            ("no_floating_graphs",
             FixedValue(
                 True,
                 title=_("Display graphs among each other"),
                 totext=_("Graphs are shown among each other"),
                 help=_("By default all multiple graphs in emails are displayed floating "
                        "nearby. You can enable this option to show the graphs among each "
                        "other."),
             )),
            ('bulk_sort_order',
             DropdownChoice(
                 choices=[
                     ('oldest_first', _('Oldest first')),
                     ('newest_first', _('Newest first')),
                 ],
                 help=_(
                     "With this option you can specify, whether the oldest (default) or "
                     "the newest notification should get shown at the top of the notification mail."
                 ),
                 title=_("Notification sort order for bulk notifications"),
                 default="oldest_first")),
            ("disable_multiplexing",
             FixedValue(
                 True,
                 title=_("Send seperate notifications to every recipient"),
                 totext=_("A seperate notification is send to every recipient. Recipients "
                          "cannot see which other recipients were notified."),
                 help=_("Per default only one notification is generated for all recipients. "
                        "Therefore, all recipients can see who was notified and reply to "
                        "all other recipients."),
             )),
        ]

        if not cmk.is_raw_edition():
            elements += cmk.gui.cee.plugins.wato.syncsmtp.cee_html_mail_smtp_sync_option

        return elements


@notification_parameter_registry.register
class NotificationParameterSlack(NotificationParameter):
    @property
    def ident(self):
        return "slack"

    @property
    def spec(self):
        return Dictionary(
            optional_keys=["url_prefix"],
            elements=[
                ("webhook_url",
                 CascadingDropdown(
                     title=_("Webhook-URL"),
                     help=
                     _("Webhook URL. Setup Slack Webhook " +
                       "<a href=\"https://my.slack.com/services/new/incoming-webhook/\" target=\"_blank\">here</a>"
                       "<br />For Mattermost follow the documentation "
                       "<a href=\"https://docs.mattermost.com/developer/webhooks-incoming.html\" target=\"_blank\">here</a>"
                       "<br />This URL can also be collected from the Password Store from Check_MK."
                      ),
                     choices=[("webhook_url", _("Webhook URL"), HTTPUrl(size=80,
                                                                        allow_empty=False)),
                              ("store", _("URL from password store"),
                               DropdownChoice(
                                   sorted=True,
                                   choices=passwordstore_choices,
                               ))],
                 )),
                ("url_prefix",
                 Transform(CascadingDropdown(
                     title=_("URL prefix for links to Check_MK"),
                     help=_(
                         "If you use <b>Automatic HTTP/s</b> the URL prefix for "
                         "host and service links within the notification mail "
                         "is filled automatically. "
                         "If you specify an URL prefix here, then several parts of the "
                         "slack message are armed with hyperlinks to your Check_MK GUI. In both cases "
                         "the recipient of the message can directly visit the host or "
                         "service in question in Check_MK. Specify an absolute URL including "
                         "the <tt>.../check_mk/</tt>"),
                     choices=[
                         ("automatic_http", _("Automatic HTTP")),
                         ("automatic_https", _("Automatic HTTPs")),
                         ("manual", _("Specify URL prefix"),
                          TextAscii(
                              regex="^(http|https)://.*/check_mk/$",
                              regex_error=_("The URL must begin with <tt>http</tt> or "
                                            "<tt>https</tt> and end with <tt>/check_mk/</tt>."),
                              size=64,
                              default_value=local_site_url,
                          )),
                     ],
                 ),
                           forth=transform_forth_html_mail_url_prefix,
                           back=transform_back_html_mail_url_prefix)),
            ],
        )


@notification_parameter_registry.register
class NotificationParameterVictorOPS(NotificationParameter):
    @property
    def ident(self):
        return "victorops"

    @property
    def spec(self):
        return Dictionary(
            optional_keys=["url_prefix"],
            elements=[
                ("webhook_url",
                 CascadingDropdown(
                     title=_("VictorOPS REST Endpoint"),
                     help=
                     _("Learn how to setup a REST endpoint "
                       "<a href=\"https://help.victorops.com/knowledge-base/victorops-restendpoint-integration/\" target=\"_blank\">here</a>"
                       "<br />This URL can also be collected from the Password Store from Check_MK."
                      ),
                     choices=[("webhook_url", _("REST Endpoint URL"),
                               HTTPUrl(size=80,
                                       allow_empty=False,
                                       regex=r"^https://alert\.victorops\.com/integrations/.+",
                                       regex_error=_(
                                           "The Webhook-URL must begin with "
                                           "<tt>https://alert.victorops.com/integrations</tt>"))),
                              ("store", _("URL from password store"),
                               DropdownChoice(
                                   sorted=True,
                                   choices=passwordstore_choices,
                               ))],
                 )),
                ("url_prefix",
                 Transform(CascadingDropdown(
                     style="dropdown",
                     title=_("URL prefix for links to Check_MK"),
                     help=_(
                         "If you use <b>Automatic HTTP/s</b> the URL prefix for "
                         "host and service links within the notification mail "
                         "is filled automatically. "
                         "If you specify an URL prefix here, then several parts of the "
                         "VictorOPS message are armed with hyperlinks to your Check_MK GUI. In both cases "
                         "the recipient of the message can directly visit the host or "
                         "service in question in Check_MK. Specify an absolute URL including "
                         "the <tt>.../check_mk/</tt>"),
                     choices=[
                         ("automatic_http", _("Automatic HTTP")),
                         ("automatic_https", _("Automatic HTTPs")),
                         ("manual", _("Specify URL prefix"),
                          TextAscii(
                              regex="^(http|https)://.*/check_mk/$",
                              regex_error=_("The URL must begin with <tt>http</tt> or "
                                            "<tt>https</tt> and end with <tt>/check_mk/</tt>."),
                              size=64,
                              default_value=local_site_url,
                          )),
                     ],
                 ),
                           forth=transform_forth_html_mail_url_prefix,
                           back=transform_back_html_mail_url_prefix)),
            ],
        )


@notification_parameter_registry.register
class NotificationParameterPagerDuty(NotificationParameter):
    @property
    def ident(self):
        return "pagerduty"

    @property
    def spec(self):
        return Dictionary(
            optional_keys=["url_prefix"],
            hidden_keys=["webhook_url"],
            elements=[
                ("routing_key",
                 CascadingDropdown(
                     title=_("PagerDuty Service Integration Key"),
                     help=_("After setting up a new Service in PagerDuty you will receive an "
                            "Integration key associated with that service. Copy that value here."),
                     choices=[("routing_key", _("Integration Key"), TextAscii(size=32)),
                              ("store", _("Key from password store"),
                               DropdownChoice(sorted=True, choices=passwordstore_choices))],
                 )),
                ("webhook_url",
                 FixedValue("https://events.pagerduty.com/v2/enqueue",
                            title=_("API Endpoint from PagerDuty V2"))),
                ("url_prefix",
                 Transform(CascadingDropdown(
                     style="dropdown",
                     title=_("URL prefix for links to Check_MK"),
                     help=_(
                         "If you use <b>Automatic HTTP/s</b> the URL prefix for "
                         "host and service links within the notification mail "
                         "is filled automatically. "
                         "If you specify an URL prefix here, then several parts of the "
                         "VictorOPS message are armed with hyperlinks to your Check_MK GUI. In both cases "
                         "the recipient of the message can directly visit the host or "
                         "service in question in Check_MK. Specify an absolute URL including "
                         "the <tt>.../check_mk/</tt>"),
                     choices=[
                         ("automatic_http", _("Automatic HTTP")),
                         ("automatic_https", _("Automatic HTTPs")),
                         ("manual", _("Specify URL prefix"),
                          TextAscii(
                              regex="^(http|https)://.*/check_mk/$",
                              regex_error=_("The URL must begin with <tt>http</tt> or "
                                            "<tt>https</tt> and end with <tt>/check_mk/</tt>."),
                              size=64,
                              default_value=local_site_url,
                          )),
                     ],
                 ),
                           forth=transform_forth_html_mail_url_prefix,
                           back=transform_back_html_mail_url_prefix)),
            ],
        )


@notification_parameter_registry.register
class NotificationParameterASCIIMail(NotificationParameter):
    @property
    def ident(self):
        return "asciimail"

    @property
    def spec(self):
        return Dictionary(elements=[
            ("from", EmailAddress(
                title=_("From: Address"),
                size=40,
                allow_empty=False,
            )),
            ("reply_to", EmailAddress(
                title=_("Reply-To: Address"),
                size=40,
                allow_empty=False,
            )),
            ("host_subject",
             TextUnicode(
                 title=_("Subject for host notifications"),
                 help=_("Here you are allowed to use all macros that are defined in the "
                        "notification context."),
                 default_value="Check_MK: $HOSTNAME$ - $EVENT_TXT$",
                 size=64,
             )),
            ("service_subject",
             TextUnicode(
                 title=_("Subject for service notifications"),
                 help=_("Here you are allowed to use all macros that are defined in the "
                        "notification context."),
                 default_value="Check_MK: $HOSTNAME$/$SERVICEDESC$ $EVENT_TXT$",
                 size=64,
             )),
            ("common_body",
             TextAreaUnicode(
                 title=_("Body head for both host and service notifications"),
                 rows=7,
                 cols=58,
                 monospaced=True,
                 default_value="""Host:     $HOSTNAME$
Alias:    $HOSTALIAS$
Address:  $HOSTADDRESS$
""",
             )),
            ("host_body",
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
             )),
            ("service_body",
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
             )),
            ('bulk_sort_order',
             DropdownChoice(
                 choices=[
                     ('oldest_first', _('Oldest first')),
                     ('newest_first', _('Newest first')),
                 ],
                 help=_(
                     "With this option you can specify, whether the oldest (default) or "
                     "the newest notification should get shown at the top of the notification mail."
                 ),
                 title=_("Notification sort order for bulk notifications"),
                 default="oldest_first")),
            ("disable_multiplexing",
             FixedValue(
                 True,
                 title=_("Send seperate notifications to every recipient"),
                 totext=_("A seperate notification is send to every recipient. Recipients "
                          "cannot see which other recipients were notified."),
                 help=_("Per default only one notification is generated for all recipients. "
                        "Therefore, all recipients can see who was notified and reply to "
                        "all other recipients."),
             )),
        ],)


@notification_parameter_registry.register
class NotificationParameterJIRA_ISSUES(NotificationParameter):
    @property
    def ident(self):
        return "jira_issues"

    @property
    def spec(self):
        return Dictionary(
            optional_keys=[
                'priority', 'resolution', 'host_summary', 'service_summary', 'ignore_ssl',
                'timeout', 'label'
            ],
            elements=[
                ("url", HTTPUrl(
                    title=_("JIRA URL"),
                    help=_("Configure the JIRA URL here."),
                )),
                ("ignore_ssl",
                 FixedValue(
                     True,
                     title=_("Disable SSL certificate verification"),
                     totext=_("Disable SSL certificate verification"),
                     help=_("Ignore unverified HTTPS request warnings. Use with caution."),
                 )),
                ("username",
                 TextAscii(
                     title=_("User Name"),
                     help=_("Configure the user name here."),
                     size=40,
                     allow_empty=False,
                 )),
                ("password",
                 Password(
                     title=_("Password"),
                     help=_(
                         "You need to provide a valid password to be able to send notifications."),
                     size=40,
                     allow_empty=False,
                 )),
                ("project",
                 TextAscii(
                     title=_("Project ID"),
                     help=_(
                         "The numerical JIRA project ID. If not set, it will be retrieved from a "
                         "custom user attribute named <tt>jiraproject</tt>. "
                         "If that is not set, the notification will fail."),
                     size=10,
                 )),
                ("issuetype",
                 TextAscii(
                     title=_("Issue type ID"),
                     help=_(
                         "The numerical JIRA issue type ID. If not set, it will be retrieved from a "
                         "custom user attribute named <tt>jiraissuetype</tt>. "
                         "If that is not set, the notification will fail."),
                     size=10,
                 )),
                ("host_customid",
                 TextAscii(
                     title=_("Host custom field ID"),
                     help=_("The numerical JIRA custom field ID for host problems."),
                     size=10,
                 )),
                ("service_customid",
                 TextAscii(
                     title=_("Service custom field ID"),
                     help=_("The numerical JIRA custom field ID for service problems."),
                     size=10,
                 )),
                ("monitoring",
                 HTTPUrl(
                     title=_("Monitoring URL"),
                     help=_(
                         "Configure the base URL for the Monitoring Web-GUI here. Include the site name. "
                         "Used for link to check_mk out of jira."),
                 )),
                ("priority",
                 TextAscii(
                     title=_("Priority ID"),
                     help=_(
                         "The numerical JIRA priority ID. If not set, it will be retrieved from a "
                         "custom user attribute named <tt>jirapriority</tt>. "
                         "If that is not set, the standard priority will be used."),
                     size=10,
                 )),
                ("host_summary",
                 TextUnicode(
                     title=_("Summary for host notifications"),
                     help=_("Here you are allowed to use all macros that are defined in the "
                            "notification context."),
                     default_value="Check_MK: $HOSTNAME$ - $HOSTSHORTSTATE$",
                     size=64,
                 )),
                ("service_summary",
                 TextUnicode(
                     title=_("Summary for service notifications"),
                     help=_("Here you are allowed to use all macros that are defined in the "
                            "notification context."),
                     default_value="Check_MK: $HOSTNAME$/$SERVICEDESC$ $SERVICESHORTSTATE$",
                     size=64,
                 )),
                ("label",
                 TextUnicode(
                     title=_("Label"),
                     help=_("Here you can set a custom label for new issues. "
                            "If not set, 'monitoring' will be used."),
                     size=16,
                 )),
                ("resolution",
                 TextAscii(
                     title=_("Activate resultion with following resolution transistion ID"),
                     help=_("The numerical JIRA resolution transition ID. "
                            "11 - 'To Do', 21 - 'In Progress', 31 - 'Done'"),
                     size=3,
                 )),
                ("timeout",
                 TextAscii(
                     title=_("Set optional timeout for connections to JIRA"),
                     help=_("Here you can configure timeout settings."),
                     default_value=10,
                 )),
            ],
        )


@notification_parameter_registry.register
class NotificationParameterServiceNow(NotificationParameter):
    @property
    def ident(self):
        return "servicenow"

    @property
    def spec(self):
        return Dictionary(
            required_keys=['url', 'username', 'password', 'caller'],
            elements=[
                ("url",
                 HTTPUrl(
                     title=_("Servicenow URL"),
                     help=_("Configure your servicenow URL here (eg. https://myservicenow.com)."),
                     allow_empty=False,
                 )),
                ("proxy_url", HTTPProxyReference()),
                ("username", TextAscii(
                    title=_("Username"),
                    size=40,
                    allow_empty=False,
                )),
                ("password", PasswordFromStore(
                    title=_("Password of the user"),
                    allow_empty=False,
                )),
                ("caller",
                 TextAscii(
                     title=_("Caller ID"),
                     help=_("Caller is the user on behalf of whom the incident is being reported "
                            "within servicenow. Please enter the name of the caller here."),
                 )),
                ("host_short_desc",
                 TextAscii(
                     title=_("Short description for host incidents"),
                     help=_("Text that should be set in field <tt>Short description</tt> "
                            "for host notifications."),
                     default_value="Check_MK: $HOSTNAME$ - $HOSTSHORTSTATE$",
                     size=64,
                 )),
                ("svc_short_desc",
                 TextAscii(
                     title=_("Short description for service incidents"),
                     help=_("Text that should be set in field <tt>Short description</tt> "
                            "for service notifications."),
                     default_value="Check_MK: $HOSTNAME$/$SERVICEDESC$ $SERVICESHORTSTATE$",
                     size=68,
                 )),
                ("host_desc",
                 TextAreaUnicode(title=_("Description for host incidents"),
                                 help=_("Text that should be set in field <tt>Description</tt> "
                                        "for host notifications."),
                                 rows=7,
                                 cols=58,
                                 monospaced=True,
                                 default_value="""Host: $HOSTNAME$
Event:    $EVENT_TXT$
Output:   $HOSTOUTPUT$
Perfdata: $HOSTPERFDATA$
$LONGHOSTOUTPUT$
""")),
                ("svc_desc",
                 TextAreaUnicode(title=_("Description for service incidents"),
                                 help=_("Text that should be set in field <tt>Description</tt> "
                                        "for service notifications."),
                                 rows=11,
                                 cols=58,
                                 monospaced=True,
                                 default_value="""Host: $HOSTNAME$
Service:  $SERVICEDESC$
Event:    $EVENT_TXT$
Output:   $SERVICEOUTPUT$
Perfdata: $SERVICEPERFDATA$
$LONGSERVICEOUTPUT$
""")),
                ("urgency",
                 DropdownChoice(
                     title=_("Urgency"),
                     help=_("See <a href=\"https://docs.servicenow.com/bundle/"
                            "helsinki-it-service-management/page/product/incident-management/"
                            "reference/r_PrioritizationOfIncidents.html\" target=\"_blank\">"
                            "ServiceNow Incident</a> for more information."),
                     choices=[
                         ("low", _("Low")),
                         ("medium", _("Medium")),
                         ("high", _("High")),
                     ],
                     default_value="low",
                 )),
                ("impact",
                 DropdownChoice(
                     title=_("Impact"),
                     help=_("See <a href=\"https://docs.servicenow.com/bundle/"
                            "helsinki-it-service-management/page/product/incident-management/"
                            "reference/r_PrioritizationOfIncidents.html\" target=\"_blank\">"
                            "ServiceNow Incident</a> for more information."),
                     choices=[
                         ("low", _("Low")),
                         ("medium", _("Medium")),
                         ("high", _("High")),
                     ],
                     default_value="low",
                 )),
                ("ack_state",
                 Dictionary(
                     title=_("Settings for incident state in case of acknowledgement"),
                     help=_("Here you can define the state of the incident in case of an "
                            "acknowledgement of the affected host or service problem."),
                     elements=[
                         ("start",
                          DropdownChoice(
                              title=_("State of incident if acknowledgement is set"),
                              help=_("Here you can define the state of the incident in case of an "
                                     "acknowledgement of the host or service problem."),
                              choices=[
                                  ("none", _("Don't change state")),
                                  ("new", _("New")),
                                  ("progress", _("In Progress")),
                                  ("hold", _("On Hold")),
                                  ("resolved", _("Resolved")),
                                  ("closed", _("Closed")),
                                  ("canceled", _("Canceled")),
                              ],
                              default_value="none",
                          )),
                     ],
                 )),
                ("dt_state",
                 Dictionary(
                     title=_("Settings for incident state in case of downtime"),
                     help=_("Here you can define the state of the incident in case of a "
                            "downtime of the affected host or service."),
                     elements=[
                         ("start",
                          DropdownChoice(
                              title=_("State of incident if downtime is set"),
                              help=_("Here you can define the state of the incident in case of an "
                                     "acknowledgement of the host or service problem."),
                              choices=[
                                  ("none", _("Don't change state")),
                                  ("new", _("New")),
                                  ("progress", _("In Progress")),
                                  ("hold", _("On Hold")),
                                  ("resolved", _("Resolved")),
                                  ("closed", _("Closed")),
                                  ("canceled", _("Canceled")),
                              ],
                              default_value="none",
                          )),
                         ("end",
                          DropdownChoice(
                              title=_("State of incident if downtime expires"),
                              help=_("Here you can define the state of the incident in case of an "
                                     "ending acknowledgement of the host or service problem."),
                              choices=[
                                  ("none", _("Don't change state")),
                                  ("new", _("New")),
                                  ("progress", _("In Progress")),
                                  ("hold", _("On Hold")),
                                  ("resolved", _("Resolved")),
                                  ("closed", _("Closed")),
                                  ("canceled", _("Canceled")),
                              ],
                              default_value="none",
                          )),
                     ],
                 )),
                ("timeout",
                 TextAscii(title=_("Set optional timeout for connections to servicenow"),
                           help=_("Here you can configure timeout settings in seconds."),
                           default_value=10,
                           size=3)),
            ],
        )


@notification_parameter_registry.register
class NotificationParameterOpsgenie(NotificationParameter):
    @property
    def ident(self):
        return "opsgenie_issues"

    @property
    def spec(self):
        return Dictionary(
            required_keys=[
                'password',
            ],
            elements=[
                ("password",
                 PasswordFromStore(
                     title=_("API Key to use. Depending on your opsgenie "
                             "subscription you can use global or team integration api "
                             "keys."),
                     allow_empty=False,
                 )),
                ("owner",
                 TextUnicode(
                     title=_("Owner"),
                     help_=("Sets the user of the alert. "
                            "Display name of the request owner."),
                     size=100,
                     allow_empty=False,
                 )),
                ("source",
                 TextUnicode(
                     title=_("Source"),
                     help=_("Source field of the alert. Default value is IP "
                            "address of the incoming request."),
                     size=16,
                 )),
                ('priority',
                 DropdownChoice(title=_("Priority"),
                                choices=[
                                    ('P1', _('P1 - Critical')),
                                    ('P2', _('P2 - High')),
                                    ('P3', _('P3 - Moderate')),
                                    ('P4', _('P4 - Low')),
                                    ('P5', _('P5 - Informational')),
                                ],
                                default="P3")),
                ("note_created",
                 TextUnicode(
                     title=_("Note while creating"),
                     help=_("Additional note that will be added while creating the alert."),
                     default_value="Alert created by Check_MK",
                 )),
                ("note_closed",
                 TextUnicode(
                     title=_("Note while closing"),
                     help=_("Additional note that will be added while closing the alert."),
                     default_value="Alert closed by Check_MK",
                 )),
                ("host_msg",
                 TextUnicode(
                     title=_("Description for host alerts"),
                     help=_("Description field of host alert that is generally "
                            "used to provide a detailed information about the "
                            "alert."),
                     default_value="Check_MK: $HOSTNAME$ - $HOSTSHORTSTATE$",
                     size=64,
                 )),
                ("svc_msg",
                 TextUnicode(
                     title=_("Description for service alerts"),
                     help=_("Description field of service alert that is generally "
                            "used to provide a detailed information about the "
                            "alert."),
                     default_value="Check_MK: $HOSTNAME$/$SERVICEDESC$ $SERVICESHORTSTATE$",
                     size=68,
                 )),
                ("host_desc",
                 TextAreaUnicode(title=_("Message for host alerts"),
                                 rows=7,
                                 cols=58,
                                 monospaced=True,
                                 default_value="""Host: $HOSTNAME$
Event:    $EVENT_TXT$
Output:   $HOSTOUTPUT$
Perfdata: $HOSTPERFDATA$
$LONGHOSTOUTPUT$
""")),
                ("svc_desc",
                 TextAreaUnicode(title=_("Message for service alerts"),
                                 rows=11,
                                 cols=58,
                                 monospaced=True,
                                 default_value="""Host: $HOSTNAME$
Service:  $SERVICEDESC$
Event:    $EVENT_TXT$
Output:   $SERVICEOUTPUT$
Perfdata: $SERVICEPERFDATA$
$LONGSERVICEOUTPUT$
""")),
                ("teams",
                 ListOfStrings(
                     title=_("Responsible teams"),
                     help=_("Team names which will be responsible for the alert. "
                            "If the API Key belongs to a team integration, "
                            "this field will be overwritten with the owner "
                            "team."),
                     allow_empty=False,
                     orientation="horizontal",
                 )),
                ("actions",
                 ListOfStrings(
                     title=_("Actions"),
                     help=_("Custom actions that will be available for the alert."),
                     allow_empty=False,
                     orientation="horizontal",
                 )),
                ("tags",
                 ListOfStrings(
                     title=_("Tags"),
                     help=_("Tags of the alert."),
                     allow_empty=False,
                     orientation="horizontal",
                 )),
                ("entity",
                 TextUnicode(
                     title=_("Entity"),
                     help=_("Is used to specify which domain the alert is related to."),
                     allow_empty=False,
                     size=68,
                 )),
            ],
        )


@notification_parameter_registry.register
class NotificationParameterMKEventDaemon(NotificationParameter):
    @property
    def ident(self):
        return "mkeventd"

    @property
    def spec(self):
        return Dictionary(elements=[
            ("facility",
             DropdownChoice(
                 title=_("Syslog Facility to use"),
                 help=_("The notifications will be converted into syslog messages with "
                        "the facility that you choose here. In the Event Console you can "
                        "later create a rule matching this facility."),
                 choices=mkeventd.syslog_facilities,
             )),
            ("remote",
             IPv4Address(
                 title=_("IP Address of remote Event Console"),
                 help=_("If you set this parameter then the notifications will be sent via "
                        "syslog/UDP (port 514) to a remote Event Console or syslog server."),
             )),
        ],)


@notification_parameter_registry.register
class NotificationParameterSpectrum(NotificationParameter):
    @property
    def ident(self):
        return "spectrum"

    @property
    def spec(self):
        return Dictionary(
            optional_keys=None,
            elements=[
                ("destination",
                 IPv4Address(title=_("Destination IP"),
                             help=_("IP Address of the Spectrum server receiving the SNMP trap"))),
                ("community",
                 Password(
                     title=_("SNMP Community"),
                     help=_("SNMP Community for the SNMP trap"),
                 )),
                ("baseoid",
                 TextAscii(title=_("Base OID"),
                           help=_("The base OID for the trap content"),
                           default_value="1.3.6.1.4.1.1234")),
            ],
        )


@notification_parameter_registry.register
class NotificationParameterPushover(NotificationParameter):
    @property
    def ident(self):
        return "pushover"

    @property
    def spec(self):
        return Dictionary(
            optional_keys=["url_prefix", "proxy_url", "priority", "sound"],
            elements=[
                ("api_key",
                 TextAscii(
                     title=_("API Key"),
                     help=
                     _("You need to provide a valid API key to be able to send push notifications "
                       "using Pushover. Register and login to <a href=\"https://www.pushover.net\" "
                       "target=\"_blank\">Pushover</a>, thn create your Check_MK installation as "
                       "application and obtain your API key."),
                     size=40,
                     allow_empty=False,
                     regex="[a-zA-Z0-9]{30}",
                 )),
                ("recipient_key",
                 TextAscii(
                     title=_("User / Group Key"),
                     help=_("Configure the user or group to receive the notifications by providing "
                            "the user or group key here. The key can be obtained from the Pushover "
                            "website."),
                     size=40,
                     allow_empty=False,
                     regex="[a-zA-Z0-9]{30}",
                 )),
                ("url_prefix",
                 TextAscii(
                     title=_("URL prefix for links to Check_MK"),
                     help=_("If you specify an URL prefix here, then several parts of the "
                            "email body are armed with hyperlinks to your Check_MK GUI, so "
                            "that the recipient of the email can directly visit the host or "
                            "service in question in Check_MK. Specify an absolute URL including "
                            "the <tt>.../check_mk/</tt>"),
                     regex="^(http|https)://.*/check_mk/$",
                     regex_error=_("The URL must begin with <tt>http</tt> or "
                                   "<tt>https</tt> and end with <tt>/check_mk/</tt>."),
                     size=64,
                     default_value=local_site_url,
                 )),
                (
                    "proxy_url",
                    Transform(
                        HTTPProxyReference(),
                        # Transform legacy explicit TextAscii() proxy URL
                        forth=lambda v: ("url", v) if isinstance(v, str) else v,
                    )),
                ("priority",
                 Transform(
                     CascadingDropdown(
                         title=_("Priority"),
                         choices=[
                             ("2",
                              _("Emergency: Repeat push notification in intervalls till expire time."
                               ),
                              Tuple(elements=[
                                  Age(title=_("Retry time")),
                                  Age(title=_("Expire time")),
                                  TextAscii(
                                      title=_("Receipt"),
                                      help=
                                      _("The receipt can be used to periodically poll receipts API to get "
                                        "the status of the notification. "
                                        "See <a href=\"https://pushover.net/api#receipt\" target=\"_blank\">"
                                        "Pushover receipts and callbacks</a> for more information."
                                       ),
                                      size=40,
                                      regex="[a-zA-Z0-9]{0,30}"),
                              ])),
                             ("1", _("High: Push notification alerts bypass quiet hours")),
                             ("0", _("Normal: Regular push notification (default)")),
                             ("-1", _("Low: No sound/vibration but show popup")),
                             ("-2", _("Lowest: No notification, update badge number")),
                         ],
                         default_value="0",
                     ),
                     forth=self._transform_forth_pushover_priority,
                     back=self._transform_back_pushover_priority,
                 )),
                ("sound",
                 DropdownChoice(
                     title=_("Select sound"),
                     help=_(
                         "See <a href=\"https://pushover.net/api#sounds\" target=\"_blank\">"
                         "Pushover sounds</a> for more information and trying out available sounds."
                     ),
                     choices=[
                         ("none", _("None (silent)")),
                         ("alien", _("Alien Alarm (long)")),
                         ("bike", _("Bike")),
                         ("bugle", _("Bugle")),
                         ("cashregister", _("Cash Register")),
                         ("classical", _("Classical")),
                         ("climb", _("Climb (long)")),
                         ("cosmic", _("Cosmic")),
                         ("echo", _("Pushover Echo (long)")),
                         ("falling", _("Falling")),
                         ("gamelan", _("Gamelan")),
                         ("incoming", _("Incoming")),
                         ("intermission", _("Intermission")),
                         ("magic", _("Magic")),
                         ("mechanical", _("Mechanical")),
                         ("persistent", _("Persistent (long)")),
                         ("pianobar", _("Piano Bar")),
                         ("pushover", _("Pushover")),
                         ("siren", _("Siren")),
                         ("spacealarm", _("Space Alarm")),
                         ("tugboat", _("Tug Boat")),
                         ("updown", _("Up Down (long)")),
                     ],
                     default_value="none")),
            ],
        )

    # We have to transform because 'add_to_event_context'
    # in modules/events.py can't handle complex data structures
    def _transform_back_pushover_priority(self, params):
        if isinstance(params, tuple):
            return {
                "priority": "2",
                "retry": params[1][0],
                "expire": params[1][1],
                "receipts": params[1][2]
            }
        return params

    def _transform_forth_pushover_priority(self, params):
        if isinstance(params, dict):
            return (params['priority'], (params["retry"], params["expire"], params["receipts"]))
        return params
