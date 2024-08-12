#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import Dictionary, FixedValue, HTTPUrl, Password, TextInput

from ._base import NotificationParameter


class NotificationParameterJiraIssues(NotificationParameter):
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
                        title=_("Jira URL"),
                        help=_("Configure the Jira URL here."),
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
                            "The numerical Jira project ID. If not set, it will be retrieved from a "
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
                            "The numerical Jira issue type ID. If not set, it will be retrieved from a "
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
                        help=_("The numerical Jira custom field ID for host problems."),
                        size=10,
                    ),
                ),
                (
                    "service_customid",
                    TextInput(
                        title=_("Service custom field ID"),
                        help=_("The numerical Jira custom field ID for service problems."),
                        size=10,
                    ),
                ),
                (
                    "site_customid",
                    TextInput(
                        title=_("Site custom field ID"),
                        help=_(
                            "The numerical ID of the Jira custom field for sites. "
                            "Please use this option if you have multiple sites in a "
                            "distributed setup which send their notifications "
                            "to the same Jira instance."
                        ),
                        size=10,
                    ),
                ),
                (
                    "monitoring",
                    HTTPUrl(
                        title=_("Monitoring URL"),
                        help=_(
                            "Configure the base URL for the monitoring web-GUI here. Include the site name. "
                            "Used for linking to Checkmk out of Jira."
                        ),
                    ),
                ),
                (
                    "priority",
                    TextInput(
                        title=_("Priority ID"),
                        help=_(
                            "The numerical Jira priority ID. If not set, it will be retrieved from a "
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
                            "The numerical Jira resolution transition ID. "
                            "11 - 'To Do', 21 - 'In Progress', 31 - 'Done'"
                        ),
                        size=3,
                    ),
                ),
                (
                    "timeout",
                    TextInput(
                        title=_("Set optional timeout for connections to Jira"),
                        help=_("Here you can configure timeout settings."),
                        default_value="10",
                    ),
                ),
            ],
        )
