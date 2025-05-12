#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FieldSize,
    FixedValue,
    Integer,
    migrate_to_password,
    migrate_to_proxy,
    Password,
    Proxy,
    String,
)
from cmk.rulesets.v1.form_specs.validators import LengthInRange, NumberInRange

from ._helpers import notification_macro_help_fs


def form_spec() -> Dictionary:
    return Dictionary(
        title=Title("Jira parameters"),
        elements={
            "url": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Jira URL"),
                    help_text=Help("Configure the Jira URL here."),
                ),
            ),
            "ignore_ssl": DictElement(
                parameter_form=FixedValue(
                    value=True,
                    title=Title("Disable SSL certificate verification"),
                    label=Label("Disable SSL certificate verification"),
                    help_text=Help("Ignore unverified HTTPS request warnings. Use with caution."),
                ),
            ),
            "proxy_url": DictElement(parameter_form=Proxy(migrate=migrate_to_proxy)),
            "auth": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    title=Title("Authentication"),
                    prefill=DefaultValue("auth_basic"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="auth_basic",
                            title=Title("Basic authentication"),
                            parameter_form=Dictionary(
                                elements={
                                    "username": DictElement(
                                        required=True,
                                        parameter_form=String(
                                            title=Title("Username"),
                                            help_text=Help("Configure the user name here."),
                                            custom_validate=[LengthInRange(min_value=1)],
                                        ),
                                    ),
                                    "password": DictElement(
                                        required=True,
                                        parameter_form=Password(
                                            title=Title("Password"),
                                            help_text=Help(
                                                "If you are still using "
                                                "%s, we recommend "
                                                "switching to an PAT/API "
                                                "token, as the password "
                                                "authentication is "
                                                "deprecated.",
                                            )
                                            % "<a href='https://developer.atlassian.com/cloud/jira/platform/deprecation-notice-basic-auth-and-cookie-based-auth/' target='_blank'>basic authentication with a password</a>",
                                            custom_validate=[LengthInRange(min_value=1)],
                                            migrate=migrate_to_password,
                                        ),
                                    ),
                                },
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="auth_token",
                            title=Title("API/PAT token"),
                            parameter_form=Dictionary(
                                elements={
                                    "token": DictElement(
                                        required=True,
                                        parameter_form=Password(
                                            title=Title("API or personal access token"),
                                            custom_validate=[LengthInRange(min_value=1)],
                                            help_text=Help(
                                                "Enter the %s to "
                                                "connect Checkmk to "
                                                "self-hosted Jira or "
                                                "enter the %s to connect "
                                                "to Jira Cloud."
                                            )
                                            % (
                                                "<a href='https://confluence.atlassian.com/enterprise/using-personal-access-tokens-1026032365.html' target  ='_blank'>personal access token</a>",
                                                "<a href='https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-accoun    t/#Create-an-API-token' target='_blank'>API token</a>",
                                            ),
                                        ),
                                    ),
                                },
                            ),
                        ),
                    ],
                ),
            ),
            "project": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Project ID"),
                    help_text=Help(
                        "The numerical Jira project ID. If not set, it will be retrieved from a "
                        "custom user attribute named <tt>jiraproject</tt>. "
                        "If that is not set, the notification will fail."
                    ),
                    field_size=FieldSize.SMALL,
                ),
            ),
            "issuetype": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Issue type ID"),
                    help_text=Help(
                        "The numerical Jira issue type ID. If not set, it will be retrieved from a "
                        "custom user attribute named <tt>jiraissuetype</tt>. "
                        "If that is not set, the notification will fail."
                    ),
                    field_size=FieldSize.SMALL,
                ),
            ),
            "host_customid": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Host custom field ID"),
                    help_text=Help("The numerical Jira custom field ID for host problems."),
                    field_size=FieldSize.SMALL,
                    custom_validate=[LengthInRange(min_value=1)],
                ),
            ),
            "service_customid": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Service custom field ID"),
                    help_text=Help("The numerical Jira custom field ID for service problems."),
                    field_size=FieldSize.SMALL,
                    custom_validate=[LengthInRange(min_value=1)],
                ),
            ),
            "site_customid": DictElement(
                parameter_form=String(
                    title=Title("Site custom field ID"),
                    help_text=Help(
                        "The numerical ID of the Jira custom field for sites. "
                        "Please use this option if you have multiple sites in a "
                        "distributed setup which send their notifications "
                        "to the same Jira instance."
                    ),
                    field_size=FieldSize.SMALL,
                ),
            ),
            "monitoring": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Monitoring URL"),
                    help_text=Help(
                        "Configure the base URL for the monitoring web GUI here. Include the site name. "
                        "Used for linking to Checkmk out of Jira."
                    ),
                ),
            ),
            "assign": DictElement(
                parameter_form=String(
                    title=Title("Assignee"),
                    custom_validate=[LengthInRange(min_value=1)],
                    help_text=Help(
                        "Assign created issues to "
                        "defined user. This is the user name "
                        "of the user (not email)."
                    ),
                ),
            ),
            "priority": DictElement(
                parameter_form=String(
                    title=Title("Priority ID"),
                    help_text=Help(
                        "The numerical Jira priority ID. If not set, it will be retrieved from a "
                        "custom user attribute named <tt>jirapriority</tt>. "
                        "If that is not set, the standard priority will be used."
                    ),
                    field_size=FieldSize.SMALL,
                ),
            ),
            "host_summary": DictElement(
                parameter_form=String(
                    title=Title("Summary for host notifications"),
                    help_text=Help(
                        "Here you are allowed to use all macros that are defined in the "
                        "notification context."
                    ),
                    prefill=DefaultValue("Check_MK: $HOSTNAME$ - $HOSTSHORTSTATE$"),
                    field_size=FieldSize.LARGE,
                ),
            ),
            "service_summary": DictElement(
                parameter_form=String(
                    title=Title("Summary for service notifications"),
                    help_text=Help(
                        "Here you are allowed to use all macros that are defined in the "
                        "notification context."
                    ),
                    prefill=DefaultValue(
                        "Check_MK: $HOSTNAME$/$SERVICEDESC$ - $SERVICESHORTSTATE$"
                    ),
                    field_size=FieldSize.LARGE,
                ),
            ),
            "label": DictElement(
                parameter_form=String(
                    title=Title("Label"),
                    help_text=Help(
                        "Set a custom label for new issues. If not set, "
                        "'monitoring' will be used.<br><br>%s"
                    )
                    % notification_macro_help_fs(),
                    field_size=FieldSize.SMALL,
                ),
            ),
            "graphs_per_notification": DictElement(
                parameter_form=Integer(
                    title=Title("Attach graphs"),
                    label=Label("Attach up to"),
                    unit_symbol="graphs",
                    help_text=Help(
                        "Attach graphs and limit the number of graphs that are attached to "
                        "an issue."
                    ),
                    prefill=DefaultValue(5),
                    custom_validate=[NumberInRange(min_value=0)],
                ),
            ),
            "resolution": DictElement(
                parameter_form=String(
                    title=Title("Activate resolution with following resolution transition ID"),
                    help_text=Help(
                        "The numerical Jira resolution transition ID. "
                        "11 - 'To Do', 21 - 'In Progress', 31 - 'Done'"
                    ),
                    field_size=FieldSize.SMALL,
                ),
            ),
            "timeout": DictElement(
                parameter_form=String(
                    title=Title("Set optional timeout for connections to Jira"),
                    help_text=Help("Here you can configure timeout settings."),
                    prefill=DefaultValue("10"),
                ),
            ),
        },
        migrate=_migrate_auth_section,
    )


def _migrate_auth_section(params: object) -> dict[str, object]:
    assert isinstance(params, dict)
    match params:
        case {"auth": _}:
            return params
        case {"username": username, "password": password, **rest}:
            rest["auth"] = (
                "auth_basic",
                {"username": username, "password": ("password", password)},
            )
            return rest
        case _:
            raise TypeError(f"Unexpected params format: {params!r}")
