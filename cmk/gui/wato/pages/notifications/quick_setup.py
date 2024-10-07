#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import Literal

from cmk.utils.user import UserId

from cmk.gui.form_specs.converter import Tuple
from cmk.gui.form_specs.private import (
    DictionaryExtended,
    ListExtended,
    ListOfStrings,
    SingleChoiceElementExtended,
    SingleChoiceExtended,
)
from cmk.gui.form_specs.vue.shared_type_defs import DictionaryLayout, ListOfStringsLayout
from cmk.gui.i18n import _
from cmk.gui.quick_setup.v0_unstable._registry import QuickSetupRegistry
from cmk.gui.quick_setup.v0_unstable.predefined import recaps
from cmk.gui.quick_setup.v0_unstable.setups import QuickSetup, QuickSetupSaveAction, QuickSetupStage
from cmk.gui.quick_setup.v0_unstable.type_defs import (
    GeneralStageErrors,
    ParsedFormData,
    QuickSetupId,
    StageIndex,
)
from cmk.gui.quick_setup.v0_unstable.widgets import FormSpecId, FormSpecWrapper, Widget
from cmk.gui.userdb import load_users
from cmk.gui.wato._group_selection import sorted_contact_group_choices
from cmk.gui.watolib.mode import mode_url

from cmk.rulesets.v1 import Label, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    FixedValue,
    HostState,
    InputHint,
    ServiceState,
    SingleChoice,
    SingleChoiceElement,
    String,
)
from cmk.rulesets.v1.form_specs.validators import EmailAddress


def _host_states() -> Sequence[tuple[int, Title]]:
    return [
        (-1, Title("Any")),
        (HostState.UP, Title("UP")),
        (HostState.DOWN, Title("DOWN")),
        (HostState.UNREACH, Title("UNREACHABLE")),
    ]


def _service_states() -> Sequence[tuple[int, Title]]:
    return [
        (-1, Title("Any")),
        (ServiceState.OK, Title("OK")),
        (ServiceState.WARN, Title("WARN")),
        (ServiceState.CRIT, Title("CRIT")),
        (ServiceState.UNKNOWN, Title("UNKNOWN")),
    ]


def _get_states(what: Literal["host", "service"]) -> Sequence[tuple[int, Title]]:
    match what:
        case "host":
            return _host_states()
        case "service":
            return _service_states()
        case _:
            raise ValueError(f"Invalid value for 'what': {what}")


def _event_choices(what: Literal["host", "service"]) -> Sequence[CascadingSingleChoiceElement]:
    return [
        CascadingSingleChoiceElement(
            name="status_change",
            title=Title("Status change"),
            parameter_form=Tuple(
                layout="horizontal",
                elements=[
                    SingleChoiceExtended(
                        label=Label("From"),
                        prefill=DefaultValue(-1),
                        type=int,
                        elements=[
                            SingleChoiceElementExtended(name=state, title=title)
                            for state, title in _get_states(what)
                        ],
                    ),
                    SingleChoiceExtended(
                        label=Label("to"),
                        prefill=DefaultValue(1) if what == "host" else DefaultValue(2),
                        type=int,
                        elements=[
                            SingleChoiceElementExtended(name=state, title=title)
                            for state, title in _get_states(what)
                        ],
                    ),
                ],
            ),
        ),
        CascadingSingleChoiceElement(
            name="downtime",
            title=Title("Start or end of downtime"),
            parameter_form=FixedValue(value=None),
        ),
        CascadingSingleChoiceElement(
            name="acknowledgement",
            title=Title("Acknowledgement of problem"),
            parameter_form=FixedValue(value=None),
        ),
        CascadingSingleChoiceElement(
            name="flapping_state",
            title=Title("Start or end of flapping state"),
            parameter_form=FixedValue(value=None),
        ),
        CascadingSingleChoiceElement(
            name="alert_handler",
            title=Title("Alert handler execution"),
            parameter_form=SingleChoice(
                prefill=DefaultValue("success"),
                elements=[
                    SingleChoiceElement(name="success", title=Title("Success")),
                    SingleChoiceElement(name="failure", title=Title("Failure")),
                ],
            ),
        ),
    ]


def _validate_at_least_one_event(
    _quick_setup_id: QuickSetupId,
    _stage_index: StageIndex,
    form_data: ParsedFormData,
) -> GeneralStageErrors:
    if not form_data[FormSpecId("triggering_events")].get("host_events") and not form_data[
        FormSpecId("triggering_events")
    ].get("service_events"):
        return [
            "No triggering events selected. "
            "Please select at least one event to trigger the notification."
        ]
    return []


def triggering_events() -> QuickSetupStage:
    def _components() -> Sequence[Widget]:
        return [
            FormSpecWrapper(
                id=FormSpecId("triggering_events"),
                form_spec=DictionaryExtended(
                    layout=DictionaryLayout.two_columns,
                    prefill=DefaultValue(
                        {
                            "host_events": [
                                ("status_change", (-1, HostState.DOWN)),
                                ("status_change", (-1, HostState.UP)),
                            ],
                            "service_events": [
                                ("status_change", (-1, ServiceState.CRIT)),
                                ("status_change", (-1, ServiceState.UNKNOWN)),
                                ("status_change", (-1, ServiceState.WARN)),
                                ("status_change", (-1, ServiceState.OK)),
                            ],
                        }
                    ),
                    elements={
                        "host_events": DictElement(
                            parameter_form=ListExtended(
                                title=Title("Host events"),
                                prefill=DefaultValue([]),
                                element_template=CascadingSingleChoice(
                                    # TODO: add horizontal layout (CMK-18894)
                                    elements=_event_choices("host"),
                                ),
                                add_element_label=Label("Add event"),
                                editable_order=False,
                            )
                        ),
                        "service_events": DictElement(
                            parameter_form=ListExtended(
                                title=Title("Service events"),
                                prefill=DefaultValue([]),
                                element_template=CascadingSingleChoice(
                                    # TODO: add horizontal layout (CMK-18894)
                                    elements=_event_choices("service"),
                                ),
                                add_element_label=Label("Add event"),
                                editable_order=False,
                            )
                        ),
                        "ec_alerts": DictElement(
                            parameter_form=FixedValue(
                                title=Title("Event console alerts"),
                                value=None,
                            ),
                        ),
                    },
                ),
            )
        ]

    return QuickSetupStage(
        title=_("Triggering events"),
        configure_components=_components,
        custom_validators=[_validate_at_least_one_event],
        recap=[recaps.recaps_form_spec],
        button_label=_("Next step: Specify host/services"),
    )


def filter_for_hosts_and_services() -> QuickSetupStage:
    def _components() -> Sequence[Widget]:
        return []

    return QuickSetupStage(
        title=_("Filter for hosts/services"),
        sub_title=_(
            "Apply filters to specify which hosts and services are affected by this "
            "notification rule."
        ),
        configure_components=_components,
        custom_validators=[],
        recap=[],
        button_label=_("Next step: Notification method (plug-in)"),
    )


def notification_method() -> QuickSetupStage:
    def _components() -> Sequence[Widget]:
        return []

    return QuickSetupStage(
        title=_("Notification method (plug-in)"),
        sub_title=_("What should be send out?"),
        configure_components=_components,
        custom_validators=[],
        recap=[],
        button_label=_("Next step: Recipient"),
    )


def _get_sorted_users() -> list[tuple[UserId, str]]:
    return sorted(
        (name, f"{name} - {user.get("alias", name)}") for name, user in load_users().items()
    )


def _contact_group_choice() -> SingleChoice:
    return SingleChoice(
        prefill=InputHint(Title("Select contact group")),
        elements=[
            SingleChoiceElement(
                name=ident,
                title=Title(title),  # pylint: disable=localization-of-non-literal-string
            )
            for ident, title in sorted_contact_group_choices()
        ],
    )


def recipient() -> QuickSetupStage:
    def _components() -> Sequence[Widget]:
        return [
            FormSpecWrapper(
                id=FormSpecId("recipient"),
                form_spec=ListExtended(
                    title=Title("Recipients"),
                    prefill=DefaultValue([("all_contacts_affected", None)]),
                    element_template=CascadingSingleChoice(
                        # TODO: add horizontal layout (CMK-18894)
                        elements=[
                            CascadingSingleChoiceElement(
                                title=Title("All contacts of the affected object"),
                                name="all_contacts_affected",
                                parameter_form=FixedValue(value=None),
                            ),
                            CascadingSingleChoiceElement(
                                title=Title("All users with an email address"),
                                name="all_email_users",
                                parameter_form=FixedValue(value=None),
                            ),
                            CascadingSingleChoiceElement(
                                title=Title("Contact group"),
                                name="contact_group",
                                parameter_form=_contact_group_choice(),
                            ),
                            CascadingSingleChoiceElement(
                                title=Title("Explicit email addresses"),
                                name="explicit_email_addresses",
                                parameter_form=ListOfStrings(
                                    layout=ListOfStringsLayout.vertical,
                                    string_spec=String(custom_validate=[EmailAddress()]),
                                ),
                            ),
                            CascadingSingleChoiceElement(
                                title=Title("Restrict previous options to"),
                                name="restrict_previous",
                                parameter_form=CascadingSingleChoice(
                                    # TODO: add horizontal layout (CMK-18894)
                                    prefill=DefaultValue("contact_group"),
                                    elements=[
                                        CascadingSingleChoiceElement(
                                            name="contact_group",
                                            title=Title("Users of contact groups"),
                                            parameter_form=ListOfStrings(
                                                string_spec=_contact_group_choice(),
                                            ),
                                        ),
                                        CascadingSingleChoiceElement(
                                            name="custom_macros",
                                            title=Title("Custom macros"),
                                            parameter_form=ListExtended(
                                                prefill=DefaultValue([]),
                                                element_template=Tuple(
                                                    title=Title("Custom macro"),
                                                    elements=[
                                                        String(
                                                            title=Title("Name of the macro"),
                                                        ),
                                                        String(
                                                            title=Title(
                                                                "Required match (regular expression)"
                                                            ),
                                                        ),
                                                    ],
                                                ),
                                                add_element_label=Label("Add condition"),
                                            ),
                                        ),
                                    ],
                                ),
                            ),
                            CascadingSingleChoiceElement(
                                title=Title("Specific users"),
                                name="specific_users",
                                parameter_form=SingleChoice(
                                    prefill=InputHint(Title("Select user")),
                                    elements=[
                                        SingleChoiceElement(
                                            name=ident,
                                            title=Title(title),  # pylint: disable=localization-of-non-literal-string
                                        )
                                        for ident, title in _get_sorted_users()
                                    ],
                                ),
                            ),
                            CascadingSingleChoiceElement(
                                title=Title("All users"),
                                name="all_users",
                                parameter_form=FixedValue(value=None),
                            ),
                        ],
                    ),
                    add_element_label=Label("Add recipient"),
                    editable_order=False,
                ),
            )
        ]

    return QuickSetupStage(
        title=_("Recipient"),
        sub_title=_("Who should receive the notification?"),
        configure_components=_components,
        custom_validators=[],
        recap=[recaps.recaps_form_spec],
        button_label=_("Next step: Sending conditions"),
    )


def sending_conditions() -> QuickSetupStage:
    def _components() -> Sequence[Widget]:
        return []

    return QuickSetupStage(
        title=_("Sending conditions"),
        sub_title=_(
            "Specify when and how notifications are sent based on frequency, timing, and "
            "content criteria."
        ),
        configure_components=_components,
        custom_validators=[],
        recap=[],
        button_label=_("Next step: General properties"),
    )


def general_properties() -> QuickSetupStage:
    def _components() -> Sequence[Widget]:
        return []

    return QuickSetupStage(
        title=_("General properties"),
        sub_title=_(
            "Review your notification rule before applying it. They will take effect right "
            "away without 'Activate changes'."
        ),
        configure_components=_components,
        custom_validators=[],
        recap=[],
        button_label=_("Next step: Saving"),
    )


def save_and_test_action(all_stages_form_data: ParsedFormData) -> str:
    return mode_url("test_notifications")


def save_and_new_action(all_stages_form_data: ParsedFormData) -> str:
    return mode_url("test_notifications")


def register(quick_setup_registry: QuickSetupRegistry) -> None:
    quick_setup_registry.register(quick_setup_notifications)


quick_setup_notifications = QuickSetup(
    title=_("Notification rule"),
    id=QuickSetupId("notification_rule"),
    stages=[
        triggering_events,
        filter_for_hosts_and_services,
        notification_method,
        recipient,
        sending_conditions,
        general_properties,
    ],
    save_actions=[
        QuickSetupSaveAction(
            id="apply_and_test",
            label=_("Apply & test notification rule"),
            action=save_and_test_action,
        ),
        QuickSetupSaveAction(
            id="apply_and_create_new",
            label=_("Apply & create another rule"),
            action=save_and_new_action,
        ),
    ],
)
