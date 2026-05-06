#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.form_specs.unstable import ListOfStrings
from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FieldSize,
    FixedValue,
    List,
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
from cmk.rulesets.v1.form_specs.validators import LengthInRange
from cmk.shared_typing.vue_formspec_components import ListOfStringsLayout

from ._helpers import notification_macro_help_fs


def form_spec() -> Dictionary:
    return Dictionary(
        title=Title("JSM Operations parameters"),
        elements={
            "password": DictElement(
                required=True,
                parameter_form=Password(
                    title=Title("Integration API key"),
                    help_text=Help(
                        "API key of the JSM Operations integration that "
                        "should receive the alerts. Create or open an API "
                        "integration (or the dedicated Checkmk integration) "
                        "in JSM Operations and copy the value shown there."
                    ),
                    migrate=migrate_to_password,
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
            "owner": DictElement(
                parameter_form=String(
                    title=Title("Assignee"),
                    help_text=Help(
                        "Sets the assignee of the alert. JSM Operations shows this "
                        "as the alert's assignee in the alert detail view; the "
                        "value is the display name of an existing JSM user."
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
                        "Team names that will be added as responders for the "
                        "alert. The integration's own team is always implicitly "
                        "responsible; entries here add additional teams."
                    ),
                    string_spec=String(),
                    custom_validate=[LengthInRange(min_value=1)],
                    layout=ListOfStringsLayout.horizontal,
                ),
            ),
            "responders": DictElement(
                parameter_form=List(
                    title=Title("Additional responders"),
                    help_text=Help(
                        "Non-team responders to attach to the alert. JSM "
                        "Operations will route the alert to these in addition "
                        "to the responsible teams."
                    ),
                    element_template=CascadingSingleChoice(
                        prefill=DefaultValue("user"),
                        elements=[
                            CascadingSingleChoiceElement(
                                name="user",
                                title=Title("User"),
                                parameter_form=String(
                                    title=Title("Username (email)"),
                                    help_text=Help(
                                        "Username (typically the email address) "
                                        "of an existing JSM user."
                                    ),
                                    custom_validate=[LengthInRange(min_value=1)],
                                ),
                            ),
                            CascadingSingleChoiceElement(
                                name="schedule",
                                title=Title("On-call schedule"),
                                parameter_form=String(
                                    title=Title("Schedule name"),
                                    custom_validate=[LengthInRange(min_value=1)],
                                ),
                            ),
                            CascadingSingleChoiceElement(
                                name="escalation",
                                title=Title("Escalation policy"),
                                parameter_form=String(
                                    title=Title("Escalation name"),
                                    custom_validate=[LengthInRange(min_value=1)],
                                ),
                            ),
                        ],
                    ),
                    add_element_label=Label("Add responder"),
                    remove_element_label=Label("Remove responder"),
                    custom_validate=[LengthInRange(min_value=1)],
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
                            name="ack_author", title=Title("Acknowledgment author")
                        ),
                        MultipleChoiceElement(
                            name="ack_comment", title=Title("Acknowledgment comment")
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
