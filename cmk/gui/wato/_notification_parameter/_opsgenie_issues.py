#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.form_specs.private import ListOfStrings

from cmk.rulesets.v1 import Help, Label, Message, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    FieldSize,
    FixedValue,
    migrate_to_password,
    migrate_to_proxy,
    MultilineText,
    MultipleChoice,
    MultipleChoiceElement,
    Password,
    Proxy,
    SingleChoice,
    SingleChoiceElement,
    String,
)
from cmk.rulesets.v1.form_specs.validators import LengthInRange, MatchRegex
from cmk.shared_typing.vue_formspec_components import ListOfStringsLayout

from ._helpers import notification_macro_help_fs


def form_spec() -> Dictionary:
    return Dictionary(
        title=Title("Opsgenie parameters"),
        elements={
            "password": DictElement(
                required=True,
                parameter_form=Password(
                    title=Title(
                        "API Key to use. Depending on your opsgenie "
                        "subscription you can use global or team integration API "
                        "keys."
                    ),
                    migrate=migrate_to_password,
                ),
            ),
            "url": DictElement(
                parameter_form=String(
                    title=Title("Domain (only used for European accounts)"),
                    help_text=Help(
                        "If you have an european account, please set the "
                        "domain of your opsgenie. Specify an absolute URL like "
                        "https://api.eu.opsgenie.com."
                    ),
                    custom_validate=[
                        MatchRegex(
                            regex="^https://.*",
                            error_msg=Message("The URL must begin with https://"),
                        )
                    ],
                ),
            ),
            "proxy_url": DictElement(parameter_form=Proxy(migrate=migrate_to_proxy)),
            "ignore_ssl": DictElement(
                parameter_form=FixedValue(
                    value=True,
                    title=Title("Disable SSL certificate verification"),
                    label=Label("Disable SSL certificate verification"),
                    help_text=Help("Ignore unverified HTTPS request warnings. Use with caution."),
                ),
            ),
            "integration_team": DictElement(
                parameter_form=String(
                    title=Title("Integration team"),
                    help_text=Help(
                        "The name of the team where the integration was created. "
                        "If this field is set, additional information can be added to alerts."
                    ),
                    custom_validate=[LengthInRange(min_value=1)],
                ),
            ),
            "owner": DictElement(
                parameter_form=String(
                    title=Title("Owner"),
                    help_text=Help(
                        "Sets the user of the alert. Display name of the request owner."
                    ),
                    custom_validate=[LengthInRange(min_value=1)],
                ),
            ),
            "source": DictElement(
                parameter_form=String(
                    title=Title("Source"),
                    help_text=Help(
                        "Source field of the alert. Default value is IP "
                        "address of the incoming request."
                    ),
                ),
            ),
            "priority": DictElement(
                parameter_form=SingleChoice(
                    title=Title("Priority"),
                    elements=[
                        SingleChoiceElement(name="P1", title=Title("P1 - Critical")),
                        SingleChoiceElement(name="P2", title=Title("P2 - High")),
                        SingleChoiceElement(name="P3", title=Title("P3 - Moderate")),
                        SingleChoiceElement(name="P4", title=Title("P4 - Low")),
                        SingleChoiceElement(name="P5", title=Title("P5 - Informational")),
                    ],
                    prefill=DefaultValue("P3"),
                ),
            ),
            "note_created": DictElement(
                parameter_form=String(
                    title=Title("Note while creating"),
                    help_text=Help("Additional note that will be added while creating the alert."),
                    prefill=DefaultValue("Alert created by Check_MK"),
                ),
            ),
            "note_closed": DictElement(
                parameter_form=String(
                    title=Title("Note while closing"),
                    help_text=Help("Additional note that will be added while closing the alert."),
                    prefill=DefaultValue("Alert closed by Check_MK"),
                ),
            ),
            "host_msg": DictElement(
                parameter_form=String(
                    title=Title("Description for host alerts"),
                    help_text=Help(
                        "Description field of host alert that is generally "
                        "used to provide a detailed information about the "
                        "alert."
                    ),
                    prefill=DefaultValue("Check_MK: $HOSTNAME$ - $HOSTSHORTSTATE$"),
                    field_size=FieldSize.LARGE,
                ),
            ),
            "svc_msg": DictElement(
                parameter_form=String(
                    title=Title("Description for service alerts"),
                    help_text=Help(
                        "Description field of service alert that is generally "
                        "used to provide a detailed information about the "
                        "alert."
                    ),
                    prefill=DefaultValue("Check_MK: $HOSTNAME$/$SERVICEDESC$ $SERVICESHORTSTATE$"),
                    field_size=FieldSize.LARGE,
                ),
            ),
            "host_desc": DictElement(
                parameter_form=MultilineText(
                    title=Title("Message for host alerts"),
                    monospaced=True,
                    prefill=DefaultValue(
                        """Host: $HOSTNAME$
Event:    $EVENT_TXT$
Output:   $HOSTOUTPUT$
Perfdata: $HOSTPERFDATA$
$LONGHOSTOUTPUT$
""",
                    ),
                ),
            ),
            "svc_desc": DictElement(
                parameter_form=MultilineText(
                    title=Title("Message for service alerts"),
                    monospaced=True,
                    prefill=DefaultValue(
                        """Host: $HOSTNAME$
Service:  $SERVICEDESC$
Event:    $EVENT_TXT$
Output:   $SERVICEOUTPUT$
Perfdata: $SERVICEPERFDATA$
$LONGSERVICEOUTPUT$
""",
                    ),
                ),
            ),
            "teams": DictElement(
                parameter_form=ListOfStrings(
                    title=Title("Responsible teams"),
                    help_text=Help(
                        "Team names which will be responsible for the alert. "
                        "If the API Key belongs to a team integration, "
                        "this field will be overwritten with the owner "
                        "team."
                    ),
                    string_spec=String(),
                    custom_validate=[LengthInRange(min_value=1)],
                    layout=ListOfStringsLayout.horizontal,
                ),
            ),
            "actions": DictElement(
                parameter_form=ListOfStrings(
                    title=Title("Actions"),
                    help_text=Help("Custom actions that will be available for the alert."),
                    string_spec=String(),
                    custom_validate=[LengthInRange(min_value=1)],
                    layout=ListOfStringsLayout.horizontal,
                ),
            ),
            "tags": DictElement(
                parameter_form=ListOfStrings(
                    title=Title("Tags"),
                    help_text=Help("Tags of the alert.<br><br>%s") % notification_macro_help_fs(),
                    string_spec=String(),
                    custom_validate=[LengthInRange(min_value=1)],
                    layout=ListOfStringsLayout.horizontal,
                ),
            ),
            "entity": DictElement(
                parameter_form=String(
                    title=Title("Entity"),
                    help_text=Help("Is used to specify which domain the alert is related to."),
                    custom_validate=[LengthInRange(min_value=1)],
                ),
            ),
            "elements": DictElement(
                parameter_form=MultipleChoice(
                    title=Title("Extra properties"),
                    elements=[
                        MultipleChoiceElement(name="omdsite", title=Title("Site ID")),
                        MultipleChoiceElement(name="hosttags", title=Title("Tags of the host")),
                        MultipleChoiceElement(name="address", title=Title("IP address of host")),
                        MultipleChoiceElement(
                            name="abstime", title=Title("Absolute time of alert")
                        ),
                        MultipleChoiceElement(
                            name="reltime", title=Title("Relative time of alert")
                        ),
                        MultipleChoiceElement(
                            name="longoutput", title=Title("Additional plug-in output")
                        ),
                        MultipleChoiceElement(
                            name="ack_author", title=Title("Acknowledgement author")
                        ),
                        MultipleChoiceElement(
                            name="ack_comment", title=Title("Acknowledgement comment")
                        ),
                        MultipleChoiceElement(
                            name="notification_author", title=Title("Notification author")
                        ),
                        MultipleChoiceElement(
                            name="notification_comment", title=Title("Notification comment")
                        ),
                        MultipleChoiceElement(name="perfdata", title=Title("Metrics")),
                        MultipleChoiceElement(
                            name="notesurl", title=Title("Custom host/service notes URL")
                        ),
                        MultipleChoiceElement(
                            name="context", title=Title("Complete variable list (for testing)")
                        ),
                    ],
                    prefill=DefaultValue(["abstime", "address", "longoutput"]),
                ),
            ),
        },
    )
