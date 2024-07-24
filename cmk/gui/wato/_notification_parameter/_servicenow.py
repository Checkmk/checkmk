#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Alternative,
    CascadingDropdown,
    Dictionary,
    DropdownChoice,
    FixedValue,
    HTTPUrl,
    Integer,
    ListOf,
    Migrate,
    TextAreaUnicode,
    TextInput,
    Tuple,
)
from cmk.gui.wato import HTTPProxyReference, IndividualOrStoredPassword

from ._base import NotificationParameter
from ._helpers import notification_macro_help


class NotificationParameterServiceNow(NotificationParameter):
    @property
    def ident(self) -> str:
        return "servicenow"

    @property
    def spec(self) -> Dictionary:
        return Migrate(  # type: ignore[return-value]
            valuespec=Dictionary(
                title=_("Create notification with the following parameters"),
                required_keys=["url", "mgmt_type", "auth"],
                elements=[
                    (
                        "url",
                        HTTPUrl(
                            title=_("ServiceNow URL"),
                            help=_(
                                "Configure your ServiceNow URL here (e.g. https://myservicenow.com)."
                            ),
                            allow_empty=False,
                        ),
                    ),
                    ("proxy_url", HTTPProxyReference()),
                    (
                        "auth",
                        CascadingDropdown(
                            title=_("Authentication"),
                            help=_(
                                "Authentication details for communicating with "
                                "ServiceNow. If you want to create incidents, at "
                                "least the role 'itil' is required. If you want "
                                "to create cases, at least 'csm_ws_integration' "
                                "and 'sn_customerservice_agent' are required."
                            ),
                            choices=[
                                (
                                    "auth_basic",
                                    _("Basic authentication"),
                                    Dictionary(
                                        elements=[
                                            (
                                                "username",
                                                TextInput(
                                                    title=_("Login username"),
                                                    allow_empty=False,
                                                ),
                                            ),
                                            (
                                                "password",
                                                IndividualOrStoredPassword(
                                                    title=_("Password"),
                                                    allow_empty=False,
                                                ),
                                            ),
                                        ],
                                        optional_keys=[],
                                    ),
                                ),
                                (
                                    "auth_token",
                                    _("OAuth token authentication"),
                                    Dictionary(
                                        elements=[
                                            (
                                                "token",
                                                IndividualOrStoredPassword(
                                                    title=_("OAuth token"),
                                                    allow_empty=False,
                                                ),
                                            ),
                                        ],
                                        optional_keys=[],
                                    ),
                                ),
                            ],
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
            ),
            migrate=_migrate_auth_section,
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
                ("custom_fields", self._custom_fields_vs()),
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
                ("custom_fields", self._custom_fields_vs()),
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

    def _custom_fields_vs(self) -> ListOf:
        return ListOf(
            title=_("Custom fields"),
            valuespec=Tuple(
                elements=[
                    TextInput(
                        title=_("Name"),
                        help=_(
                            "Enter the technical name of the field as defined "
                            "in the ServiceNow database."
                        ),
                        size=40,
                        regex="^[-a-z0-9A-Z_]*$",
                        regex_error=_(
                            "Invalid custum field. Only the characters a-z, A-Z, "
                            "0-9, _ and - are allowed."
                        ),
                        allow_empty=False,
                    ),
                    TextInput(
                        title=_("Value"),
                        help=notification_macro_help(),
                        allow_empty=False,
                        size=60,
                    ),
                ],
                show_titles=True,
                orientation="horizontal",
            ),
        )


def _migrate_auth_section(params: dict[str, Any]) -> dict[str, Any]:
    if "auth" in params:
        return params
    username = params.pop("username")
    password = params.pop("password")
    params["auth"] = ("auth_basic", {"username": username, "password": ("password", password[1])})

    return params
