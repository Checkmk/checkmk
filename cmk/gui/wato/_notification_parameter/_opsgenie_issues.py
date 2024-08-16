#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Dictionary,
    DropdownChoice,
    ListChoice,
    ListOfStrings,
    TextAreaUnicode,
    TextInput,
)
from cmk.gui.wato import HTTPProxyReference, IndividualOrStoredPassword

from ._base import NotificationParameter
from ._helpers import notification_macro_help


class NotificationParameterOpsgenie(NotificationParameter):
    @property
    def ident(self) -> str:
        return "opsgenie_issues"

    @property
    def spec(self):
        return Dictionary(
            title=_("Create notification with the following parameters"),
            required_keys=[
                "password",
            ],
            elements=[
                (
                    "password",
                    IndividualOrStoredPassword(
                        title=_(
                            "API Key to use. Depending on your opsgenie "
                            "subscription you can use global or team integration API "
                            "keys."
                        ),
                        allow_empty=False,
                    ),
                ),
                (
                    "url",
                    TextInput(
                        title=_("Domain (only used for European accounts)"),
                        help=_(
                            "If you have an european account, please set the "
                            "domain of your opsgenie. Specify an absolute URL like "
                            "https://api.eu.opsgenie.com."
                        ),
                        regex="^https://.*",
                        regex_error=_("The URL must begin with <tt>https</tt>."),
                        size=64,
                    ),
                ),
                ("proxy_url", HTTPProxyReference()),
                (
                    "owner",
                    TextInput(
                        title=_("Owner"),
                        help=("Sets the user of the alert. " "Display name of the request owner."),
                        size=100,
                        allow_empty=False,
                    ),
                ),
                (
                    "source",
                    TextInput(
                        title=_("Source"),
                        help=_(
                            "Source field of the alert. Default value is IP "
                            "address of the incoming request."
                        ),
                        size=16,
                    ),
                ),
                (
                    "priority",
                    DropdownChoice(
                        title=_("Priority"),
                        choices=[
                            ("P1", _("P1 - Critical")),
                            ("P2", _("P2 - High")),
                            ("P3", _("P3 - Moderate")),
                            ("P4", _("P4 - Low")),
                            ("P5", _("P5 - Informational")),
                        ],
                        default_value="P3",
                    ),
                ),
                (
                    "note_created",
                    TextInput(
                        title=_("Note while creating"),
                        help=_("Additional note that will be added while creating the alert."),
                        default_value="Alert created by Check_MK",
                    ),
                ),
                (
                    "note_closed",
                    TextInput(
                        title=_("Note while closing"),
                        help=_("Additional note that will be added while closing the alert."),
                        default_value="Alert closed by Check_MK",
                    ),
                ),
                (
                    "host_msg",
                    TextInput(
                        title=_("Description for host alerts"),
                        help=_(
                            "Description field of host alert that is generally "
                            "used to provide a detailed information about the "
                            "alert."
                        ),
                        default_value="Check_MK: $HOSTNAME$ - $HOSTSHORTSTATE$",
                        size=64,
                    ),
                ),
                (
                    "svc_msg",
                    TextInput(
                        title=_("Description for service alerts"),
                        help=_(
                            "Description field of service alert that is generally "
                            "used to provide a detailed information about the "
                            "alert."
                        ),
                        default_value="Check_MK: $HOSTNAME$/$SERVICEDESC$ $SERVICESHORTSTATE$",
                        size=68,
                    ),
                ),
                (
                    "host_desc",
                    TextAreaUnicode(
                        title=_("Message for host alerts"),
                        rows=7,
                        cols=58,
                        monospaced=True,
                        default_value="""Host: $HOSTNAME$
Event:    $EVENT_TXT$
Output:   $HOSTOUTPUT$
Perfdata: $HOSTPERFDATA$
$LONGHOSTOUTPUT$
""",
                    ),
                ),
                (
                    "svc_desc",
                    TextAreaUnicode(
                        title=_("Message for service alerts"),
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
                    ),
                ),
                (
                    "teams",
                    ListOfStrings(
                        title=_("Responsible teams"),
                        help=_(
                            "Team names which will be responsible for the alert. "
                            "If the API Key belongs to a team integration, "
                            "this field will be overwritten with the owner "
                            "team."
                        ),
                        allow_empty=False,
                        orientation="horizontal",
                    ),
                ),
                (
                    "actions",
                    ListOfStrings(
                        title=_("Actions"),
                        help=_("Custom actions that will be available for the alert."),
                        allow_empty=False,
                        orientation="horizontal",
                    ),
                ),
                (
                    "tags",
                    ListOfStrings(
                        title=_("Tags"),
                        help=_("Tags of the alert.<br><br>%s") % notification_macro_help(),
                        allow_empty=False,
                        orientation="horizontal",
                    ),
                ),
                (
                    "entity",
                    TextInput(
                        title=_("Entity"),
                        help=_("Is used to specify which domain the alert is related to."),
                        allow_empty=False,
                        size=68,
                    ),
                ),
                (
                    "elements",
                    ListChoice(
                        title=_("Extra properties"),
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
                            ("notesurl", _("Custom host/service notes URL")),
                            ("context", _("Complete variable list (for testing)")),
                        ],
                        default_value=["abstime", "address", "longoutput"],
                    ),
                ),
            ],
        )
