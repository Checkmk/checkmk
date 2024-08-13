#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from cmk.utils import paths

from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Dictionary,
    DictionaryEntry,
    DropdownChoice,
    EmailAddress,
    FixedValue,
    Integer,
    ListChoice,
    TextAreaUnicode,
    TextInput,
)

from cmk.ccc.version import edition, Edition

from ._base import NotificationParameter
from ._helpers import get_url_prefix_specs, local_site_url


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
            hidden_keys=(
                ["from", "url_prefix", "disable_multiplexing", "smtp"]
                if edition(paths.omd_root) == Edition.CSE
                else []
            ),
        )

    def _parameter_elements(self) -> list[DictionaryEntry]:
        return _vs_add_common_mail_elements(
            [
                (
                    "elements",
                    ListChoice(
                        title=_("Display additional information"),
                        choices=[
                            ("omdsite", _("Site ID")),
                            ("hosttags", _("Tags of the host")),
                            ("address", _("IP address of host")),
                            ("abstime", _("Absolute time of alert")),
                            ("reltime", _("Relative time of alert")),
                            ("longoutput", _("Additional plug-in output")),
                            ("ack_author", _("Acknowledgement author")),
                            ("ack_comment", _("Acknowledgement comment")),
                            ("notification_author", _("Notification author")),
                            ("notification_comment", _("Notification comment")),
                            ("perfdata", _("Metrics")),
                            ("graph", _("Time series graph")),
                            ("notesurl", _("Custom host/service notes URL")),
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
                        local_site_url,
                        "automatic_https" if request.is_ssl_request else "automatic_http",
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
                            "size for attachements or the plug-in may run into a timeout so that a failed "
                            "notification is produced."
                        ),
                        default_value=5,
                        minvalue=0,
                    ),
                ),
            ]
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
            title=_("Create notification with the following parameters"),
            elements=elements,
            hidden_keys=(
                ["from", "disable_multiplexing"] if edition(paths.omd_root) == Edition.CSE else []
            ),
        )


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
                title=_("Send separate notifications to every recipient"),
                totext=_(
                    "A separate notification is send to every recipient. Recipients "
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
