#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _

from cmk.rulesets.v1 import Help, Message, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    DictGroup,
    Dictionary,
    FieldSize,
    Integer,
    List,
    migrate_to_password,
    migrate_to_proxy,
    MultilineText,
    Password,
    Proxy,
    SingleChoice,
    SingleChoiceElement,
    String,
)
from cmk.rulesets.v1.form_specs.validators import LengthInRange, MatchRegex, NumberInRange

from ._helpers import notification_macro_help_fs


def form_spec() -> Dictionary:
    return Dictionary(
        title=Title("ServiceNow parameters"),
        migrate=_migrate_auth_section,
        elements={
            "url": DictElement(
                parameter_form=String(
                    title=Title("ServiceNow URL"),
                    help_text=Help(
                        "Configure your ServiceNow URL here (e.g. https://myservicenow.com)."
                    ),
                    custom_validate=[LengthInRange(min_value=1)],
                ),
                required=True,
            ),
            "proxy_url": DictElement(
                parameter_form=Proxy(
                    title=Title("HTTP proxy"),
                    migrate=migrate_to_proxy,
                )
            ),
            "auth": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    title=Title("Authentication"),
                    help_text=Help(
                        "Authentication details for communicating with "
                        "ServiceNow. If you want to create incidents, at "
                        "least the role 'itil' is required. If you want "
                        "to create cases, at least 'csm_ws_integration' "
                        "and 'sn_customerservice_agent' are required."
                    ),
                    prefill=DefaultValue("auth_basic"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="auth_basic",
                            title=Title("Basic authentication"),
                            parameter_form=Dictionary(
                                elements={
                                    "username": DictElement(
                                        parameter_form=String(
                                            title=Title("Login username"),
                                            custom_validate=[LengthInRange(min_value=1)],
                                        ),
                                        required=True,
                                    ),
                                    "password": DictElement(
                                        parameter_form=Password(
                                            title=Title("Password"),
                                            migrate=migrate_to_password,
                                        ),
                                        required=True,
                                    ),
                                },
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="auth_token",
                            title=Title("OAuth token authentication"),
                            parameter_form=Dictionary(
                                elements={
                                    "token": DictElement(
                                        parameter_form=Password(
                                            title=Title("OAuth token"),
                                            migrate=migrate_to_password,
                                        ),
                                        required=True,
                                    ),
                                },
                            ),
                        ),
                    ],
                ),
            ),
            "use_site_id": DictElement(
                parameter_form=SingleChoice(
                    migrate=lambda o: "use_site_id" if o else "deactivated",
                    title=Title("Use site ID prefix"),
                    help_text=Help(
                        "Please use this option if you have multiple "
                        "sites in a distributed setup which send their "
                        "notifications to the same ServiceNow instance. "
                        "The site ID will be used as prefix for the "
                        "problem ID on incident creation."
                    ),
                    elements=[
                        SingleChoiceElement(
                            name="deactivated",
                            title=Title("Deactivated"),
                        ),
                        SingleChoiceElement(
                            name="use_site_id",
                            title=Title("Use site ID"),
                        ),
                    ],
                    prefill=DefaultValue("deactivated"),
                )
            ),
            "timeout": DictElement(
                parameter_form=String(
                    title=Title("Set optional timeout for connections to ServiceNow"),
                    help_text=Help("Here you can configure timeout settings in seconds."),
                    prefill=DefaultValue("10"),
                )
            ),
            "mgmt_type": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    title=Title("Management type"),
                    help_text=Help(
                        "With ServiceNow you can create different "
                        "types of management issues, currently "
                        "supported are indicents and cases."
                    ),
                    prefill=DefaultValue("incident"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="incident",
                            title=Title("Incident"),
                            parameter_form=_incident_fs(),
                        ),
                        CascadingSingleChoiceElement(
                            name="case",
                            title=Title("Case"),
                            parameter_form=_case_fs(),
                        ),
                    ],
                ),
            ),
        },
    )


def _incident_fs() -> Dictionary:
    return Dictionary(
        title=Title("Incident"),
        elements={
            "caller": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Caller ID"),
                    help_text=Help(
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
            "host_short_desc": DictElement(parameter_form=_host_short_desc(_("incidents"))),
            "svc_short_desc": DictElement(parameter_form=_svc_short_desc(_("incidents"))),
            "host_desc": DictElement(
                parameter_form=_host_desc(
                    title=Title("Description for host incidents"),
                    help_text=Help(
                        "Text that should be set in field <tt>Description</tt> "
                        "for host notifications."
                    ),
                ),
            ),
            "svc_desc": DictElement(
                parameter_form=_svc_desc(
                    title=Title("Description for service incidents"),
                    help_text=Help(
                        "Text that should be set in field <tt>Description</tt> "
                        "for service notifications."
                    ),
                ),
            ),
            "urgency": DictElement(
                parameter_form=SingleChoice(
                    title=Title("Urgency"),
                    help_text=Help(
                        'See <a href="https://docs.servicenow.com/bundle/'
                        "helsinki-it-service-management/page/product/incident-management/"
                        'reference/r_PrioritizationOfIncidents.html" target="_blank">'
                        "ServiceNow Incident</a> for more information."
                    ),
                    elements=[
                        SingleChoiceElement(name="low", title=Title("Low")),
                        SingleChoiceElement(name="medium", title=Title("Medium")),
                        SingleChoiceElement(name="high", title=Title("High")),
                    ],
                    prefill=DefaultValue("low"),
                ),
            ),
            "impact": DictElement(
                parameter_form=SingleChoice(
                    title=Title("Impact"),
                    help_text=Help(
                        'See <a href="https://docs.servicenow.com/bundle/'
                        "helsinki-it-service-management/page/product/incident-management/"
                        'reference/r_PrioritizationOfIncidents.html" target="_blank">'
                        "ServiceNow Incident</a> for more information."
                    ),
                    elements=[
                        SingleChoiceElement(name="low", title=Title("Low")),
                        SingleChoiceElement(name="medium", title=Title("Medium")),
                        SingleChoiceElement(name="high", title=Title("High")),
                    ],
                    prefill=DefaultValue("low"),
                ),
            ),
            "custom_fields": DictElement(parameter_form=_custom_fields_fs()),
            "ack_state": DictElement(
                parameter_form=Dictionary(
                    title=Title("Settings for incident state in case of acknowledgement"),
                    help_text=Help(
                        "Here you can define the state of the incident in case of an "
                        "acknowledgement of the affected host or service problem."
                    ),
                    elements={
                        "start": DictElement(
                            parameter_form=CascadingSingleChoice(
                                title=Title("State of incident if acknowledgement is set"),
                                help_text=Help(
                                    "Here you can define the state of the incident in case of an "
                                    "acknowledgement of the host or service problem."
                                ),
                                prefill=DefaultValue("predefined"),
                                migrate=_migrate_state_of,
                                elements=[
                                    CascadingSingleChoiceElement(
                                        name="predefined",
                                        title=Title(
                                            "State of incident if acknowledgement is set (predefined)"
                                        ),
                                        parameter_form=SingleChoice(
                                            title=Title(
                                                "State of incident if acknowledgement is set (predefined)"
                                            ),
                                            help_text=Help(
                                                "Please note that the mapping to the numeric "
                                                "ServiceNow state may be changed at your system "
                                                "and can differ from our definitions. In this case "
                                                "use the option below."
                                            ),
                                            elements=[
                                                SingleChoiceElement(name=name, title=title)
                                                for name, title in _get_state_choices("incident")
                                            ],
                                            prefill=DefaultValue("none"),
                                        ),
                                    ),
                                    CascadingSingleChoiceElement(
                                        name="integer",
                                        title=Title(
                                            "State of incident if acknowledgement is set (as integer)"
                                        ),
                                        parameter_form=Integer(
                                            title=Title(
                                                "State of incident if acknowledgement is set (as integer)"
                                            ),
                                            custom_validate=[NumberInRange(min_value=0)],
                                        ),
                                    ),
                                ],
                            ),
                        )
                    },
                ),
            ),
            "recovery_state": DictElement(parameter_form=_recovery_state_fs(_("incident"))),
            "dt_state": DictElement(
                parameter_form=Dictionary(
                    title=Title("Settings for incident state in case of downtime"),
                    help_text=Help(
                        "Here you can define the state of the incident in case of a "
                        "downtime of the affected host or service."
                    ),
                    elements={
                        "start": DictElement(
                            parameter_form=CascadingSingleChoice(
                                title=Title("State of incident if downtime is set"),
                                prefill=DefaultValue("predefined"),
                                migrate=_migrate_state_of,
                                elements=[
                                    CascadingSingleChoiceElement(
                                        name="predefined",
                                        title=Title(
                                            "State of incident if downtime is set (predefined)"
                                        ),
                                        parameter_form=SingleChoice(
                                            title=Title(
                                                "State of incident if downtime is set (predefined)"
                                            ),
                                            help_text=Help(
                                                "Please note that the mapping to the numeric "
                                                "ServiceNow state may be changed at your system "
                                                "and can differ from our definitions. In this case "
                                                "use the option below."
                                            ),
                                            elements=[
                                                SingleChoiceElement(name=name, title=title)
                                                for name, title in _get_state_choices("incident")
                                            ],
                                            prefill=DefaultValue("none"),
                                        ),
                                    ),
                                    CascadingSingleChoiceElement(
                                        name="integer",
                                        title=Title(
                                            "State of incident if downtime is set (as integer)"
                                        ),
                                        parameter_form=Integer(
                                            title=Title(
                                                "State of incident if downtime is set (as integer)"
                                            ),
                                            custom_validate=[NumberInRange(min_value=0)],
                                        ),
                                    ),
                                ],
                            ),
                        ),
                        "end": DictElement(
                            parameter_form=CascadingSingleChoice(
                                title=Title("State of incident if downtime expires"),
                                help_text=Help(
                                    "Here you can define the state of the incident in case of an "
                                    "ending acknowledgement of the host or service problem."
                                ),
                                prefill=DefaultValue("predefined"),
                                migrate=_migrate_state_of,
                                elements=[
                                    CascadingSingleChoiceElement(
                                        name="predefined",
                                        title=Title(
                                            "State of incident if downtime expires (predefined)"
                                        ),
                                        parameter_form=SingleChoice(
                                            title=Title(
                                                "State of incident if downtime expires (predefined)"
                                            ),
                                            help_text=Help(
                                                "Please note that the mapping to the numeric "
                                                "ServiceNow state may be changed at your system "
                                                "and can differ from our definitions. In this case "
                                                "use the option below."
                                            ),
                                            elements=[
                                                SingleChoiceElement(name=name, title=title)
                                                for name, title in _get_state_choices("incident")
                                            ],
                                            prefill=DefaultValue("none"),
                                        ),
                                    ),
                                    CascadingSingleChoiceElement(
                                        name="integer",
                                        title=Title(
                                            "State of incident if downtime expires (as integer)"
                                        ),
                                        parameter_form=Integer(
                                            title=Title(
                                                "State of incident if downtime expires (as integer)"
                                            ),
                                            custom_validate=[NumberInRange(min_value=0)],
                                        ),
                                    ),
                                ],
                            ),
                        ),
                    },
                ),
            ),
        },
    )


def _case_fs() -> Dictionary:
    return Dictionary(
        title=Title("Case"),
        elements={
            "host_short_desc": DictElement(parameter_form=_host_short_desc(_("cases"))),
            "svc_short_desc": DictElement(parameter_form=_svc_short_desc(_("cases"))),
            "host_desc": DictElement(
                parameter_form=_host_desc(
                    title=Title("Resolution notes for host cases"),
                    help_text=Help(
                        "Text that should be set in field <tt>Resolution notes</tt> "
                        "on recovery service notifications."
                    ),
                ),
            ),
            "svc_desc": DictElement(
                parameter_form=_svc_desc(
                    title=Title("Resolution notes for service cases"),
                    help_text=Help(
                        "Text that should be set in field <tt>Resolution notes</tt> "
                        "on recovery service notifications."
                    ),
                ),
            ),
            "priority": DictElement(
                parameter_form=SingleChoice(
                    title=Title("Priority"),
                    help_text=Help(
                        "Here you can define with which priority the case should be created."
                    ),
                    elements=[
                        SingleChoiceElement(name="low", title=Title("Low")),
                        SingleChoiceElement(name="moderate", title=Title("Moderate")),
                        SingleChoiceElement(name="high", title=Title("High")),
                        SingleChoiceElement(name="critical", title=Title("Critical")),
                    ],
                    prefill=DefaultValue("low"),
                ),
            ),
            "custom_fields": DictElement(parameter_form=_custom_fields_fs()),
            "recovery_state": DictElement(parameter_form=_recovery_state_fs(_("case"))),
        },
    )


def _host_desc(title: Title, help_text: Help) -> MultilineText:
    return MultilineText(
        title=title,
        help_text=help_text,
        monospaced=True,
        prefill=DefaultValue("""Host: $HOSTNAME$
Event:    $EVENT_TXT$
Output:   $HOSTOUTPUT$
Perfdata: $HOSTPERFDATA$
$LONGHOSTOUTPUT$
"""),
    )


def _svc_desc(title: Title, help_text: Help) -> MultilineText:
    return MultilineText(
        title=title,
        help_text=help_text,
        monospaced=True,
        prefill=DefaultValue("""Host: $HOSTNAME$
Service:  $SERVICEDESC$
Event:    $EVENT_TXT$
Output:   $SERVICEOUTPUT$
Perfdata: $SERVICEPERFDATA$
$LONGSERVICEOUTPUT$
"""),
    )


def _host_short_desc(issue_type: str) -> String:
    return String(
        title=Title("Short description for host %s") % issue_type,
        help_text=Help(
            "Text that should be set in field <tt>Short description</tt> for host notifications."
        ),
        field_size=FieldSize.LARGE,
        prefill=DefaultValue("Check_MK: $HOSTNAME$ - $HOSTSHORTSTATE$"),
    )


def _svc_short_desc(issue_type: str) -> String:
    return String(
        title=Title("Short description for service %s") % issue_type,
        help_text=Help(
            "Text that should be set in field <tt>Short description</tt> for service notifications."
        ),
        field_size=FieldSize.LARGE,
        prefill=DefaultValue("Check_MK: $HOSTNAME$/$SERVICEDESC$ $SERVICESHORTSTATE$"),
    )


def _recovery_state_fs(issue_type: str) -> Dictionary:
    return Dictionary(
        title=Title("Settings for %s state in case of recovery") % issue_type,
        help_text=Help(
            "Here you can define the state of the %s in case of a recovery "
            "of the affected host or service problem."
        )
        % issue_type,
        elements={
            "start": DictElement(
                parameter_form=CascadingSingleChoice(
                    title=Title("State of %s if recovery is set") % issue_type,
                    prefill=DefaultValue("predefined"),
                    migrate=_migrate_state_of,
                    elements=[
                        CascadingSingleChoiceElement(
                            name="predefined",
                            title=Title("State of case if recovery is set (predefined)"),
                            parameter_form=SingleChoice(
                                title=Title("State of case if recovery is set (predefined)"),
                                help_text=Help(
                                    "Please note that the mapping to the numeric "
                                    "ServiceNow state may be changed at your system "
                                    "and can differ from our definitions. In this case "
                                    "use the option below."
                                ),
                                elements=[
                                    SingleChoiceElement(name=name, title=title)
                                    for name, title in _get_state_choices("incident")
                                ],
                                prefill=DefaultValue("none"),
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="integer",
                            title=Title("State of %s if recovery is set (as integer)") % issue_type,
                            parameter_form=Integer(
                                title=Title("State of %s if recovery is set (as integer)")
                                % issue_type,
                                custom_validate=[NumberInRange(min_value=0)],
                            ),
                        ),
                    ],
                ),
            ),
        },
    )


def _get_state_choices(issue_type: str) -> list[tuple[str, Title]]:
    if issue_type == "incident":
        return [
            ("none", Title("Don't change state")),
            ("new", Title("New")),
            ("progress", Title("In Progress")),
            ("hold", Title("On Hold")),
            ("resolved", Title("Resolved")),
            ("closed", Title("Closed")),
            ("canceled", Title("Canceled")),
        ]

    # Cases
    return [
        ("none", Title("Don't change state")),
        ("new", Title("New")),
        ("closed", Title("Closed")),
        ("resolved", Title("Resolved")),
        ("open", Title("Open")),
        ("awaiting_info", Title("Awaiting info")),
    ]


def _custom_fields_fs() -> List:
    return List(
        title=Title("Custom fields"),
        element_template=Dictionary(
            migrate=_migrate_custom_fields,
            elements={
                "name": DictElement(
                    group=DictGroup(),
                    required=True,
                    parameter_form=String(
                        title=Title("Name"),
                        help_text=Help(
                            "Enter the technical name of the field as defined "
                            "in the ServiceNow database."
                        ),
                        custom_validate=[
                            LengthInRange(min_value=1),
                            MatchRegex(
                                regex="^[-a-z0-9A-Z_]*$",
                                error_msg=Message(
                                    "Invalid custom field. Only the characters a-z, A-Z, "
                                    "0-9, _ and - are allowed."
                                ),
                            ),
                        ],
                    ),
                ),
                "value": DictElement(
                    group=DictGroup(),
                    required=True,
                    parameter_form=String(
                        title=Title("Value"),
                        help_text=notification_macro_help_fs(),
                        custom_validate=[LengthInRange(min_value=1)],
                    ),
                ),
            },
        ),
    )


def _migrate_custom_fields(o: object) -> dict[str, str]:
    match o:
        case (name, value):
            assert isinstance(name, str)
            assert isinstance(value, str)
            return {"name": name, "value": value}
        case {"name": name, "value": value}:
            return {"name": name, "value": value}
        case _:
            raise TypeError(f"Invalid custom field: {o}")


def _migrate_state_of(o: object) -> tuple[str, object]:
    match o:
        case str():
            return "predefined", o
        case int():
            return "integer", o
        case ["predefined", p]:
            return "predefined", p
        case ["integer", i]:
            return "integer", i
        case _:
            raise TypeError(f"Invalid state: {o}")


def _migrate_auth_section(params):
    if "auth" in params:
        return params
    username = params.pop("username")
    password = params.pop("password")
    params["auth"] = ("auth_basic", {"username": username, "password": ("password", password[1])})

    return params
