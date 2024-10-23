#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence
from typing import cast, Literal

from cmk.utils.timeperiod import TimeperiodName
from cmk.utils.urls import is_allowed_url
from cmk.utils.user import UserId

from cmk.gui.form_specs.converter import Tuple
from cmk.gui.form_specs.private import (
    CascadingSingleChoiceExtended,
    CommentTextArea,
    DictionaryExtended,
    ListExtended,
    ListOfStrings,
    not_empty,
    SingleChoiceEditable,
    SingleChoiceElementExtended,
    SingleChoiceExtended,
)
from cmk.gui.form_specs.vue.shared_type_defs import (
    CascadingSingleChoiceLayout,
    DictionaryLayout,
    ListOfStringsLayout,
)
from cmk.gui.i18n import _
from cmk.gui.quick_setup.v0_unstable._registry import QuickSetupRegistry
from cmk.gui.quick_setup.v0_unstable.predefined import recaps
from cmk.gui.quick_setup.v0_unstable.setups import (
    QuickSetup,
    QuickSetupAction,
    QuickSetupActionMode,
    QuickSetupStage,
)
from cmk.gui.quick_setup.v0_unstable.type_defs import (
    GeneralStageErrors,
    ParsedFormData,
    QuickSetupId,
    StageIndex,
)
from cmk.gui.quick_setup.v0_unstable.widgets import FormSpecId, FormSpecWrapper, Widget
from cmk.gui.userdb import load_users
from cmk.gui.wato._group_selection import sorted_contact_group_choices
from cmk.gui.wato._notification_parameter import notification_parameter_registry
from cmk.gui.wato.pages.notifications.migrate import (
    migrate_to_event_rule,
    migrate_to_notification_quick_setup_spec,
)
from cmk.gui.wato.pages.notifications.quick_setup_types import (
    NotificationQuickSetupSpec,
)
from cmk.gui.watolib.configuration_entity.type_defs import ConfigEntityType
from cmk.gui.watolib.mode import mode_url
from cmk.gui.watolib.notifications import NotificationRuleConfigFile
from cmk.gui.watolib.timeperiods import load_timeperiods
from cmk.gui.watolib.users import notification_script_choices

from cmk.rulesets.v1 import Help, Label, Message, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FieldSize,
    FixedValue,
    HostState,
    InputHint,
    Integer,
    ServiceState,
    SingleChoice,
    SingleChoiceElement,
    String,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.form_specs.validators import EmailAddress, ValidationError


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
    if not form_data[FormSpecId("triggering_events")]:
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
                                element_template=CascadingSingleChoiceExtended(
                                    elements=_event_choices("host"),
                                    layout=CascadingSingleChoiceLayout.horizontal,
                                ),
                                add_element_label=Label("Add event"),
                                editable_order=False,
                                custom_validate=[_validate_empty_selection],
                            )
                        ),
                        "service_events": DictElement(
                            parameter_form=ListExtended(
                                title=Title("Service events"),
                                prefill=DefaultValue([]),
                                element_template=CascadingSingleChoiceExtended(
                                    elements=_event_choices("service"),
                                    layout=CascadingSingleChoiceLayout.horizontal,
                                ),
                                add_element_label=Label("Add event"),
                                editable_order=False,
                                custom_validate=[_validate_empty_selection],
                            )
                        ),
                        "ec_alerts": DictElement(
                            parameter_form=FixedValue(
                                title=Title("Event Console alerts"),
                                value="Enabled",
                            ),
                        ),
                    },
                ),
            )
        ]

    return QuickSetupStage(
        title=_("Triggering events"),
        sub_title=_("Define any events you want to be notified about."),
        configure_components=_components,
        custom_validators=[_validate_at_least_one_event],
        recap=[custom_recap_formspec_triggering_events],
        button_label=_("Next step: Specify host/services"),
    )


def custom_recap_formspec_triggering_events(
    quick_setup_id: QuickSetupId,
    stage_index: StageIndex,
    all_stages_form_data: ParsedFormData,
) -> Sequence[Widget]:
    cleaned_stages_form_data = {
        form_spec_wrapper_id: {
            form_spec_id: data
            for form_spec_id, data in form_data.items()
            if form_spec_id not in ["host_events", "service_events"] or len(data) > 0
        }
        for form_spec_wrapper_id, form_data in all_stages_form_data.items()
    }
    return recaps.recaps_form_spec(quick_setup_id, stage_index, cleaned_stages_form_data)


def _validate_empty_selection(selections: Sequence[Sequence[str | None]]) -> None:
    # TODO validation seems not to be possible for a single empty element of
    # the Tuple
    if ["", None] in selections:
        raise ValidationError(
            Message("At least one selection is missing."),
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
    def bulk_notification(
        title: Literal["always", "timeperiod"],
    ) -> DictionaryExtended:
        return DictionaryExtended(
            title=Title("Bulk notification"),
            elements={
                **(
                    {
                        "combine": DictElement(
                            required=True,
                            parameter_form=TimeSpan(
                                title=Title("Combine within last"),
                                displayed_magnitudes=[
                                    TimeMagnitude.HOUR,
                                    TimeMagnitude.MINUTE,
                                    TimeMagnitude.SECOND,
                                ],
                                prefill=DefaultValue(60.0),
                            ),
                        )
                    }
                    if title == "always"
                    else {}
                ),
                "bulking_parameters": DictElement(
                    required=True,
                    parameter_form=DictionaryExtended(
                        title=Title("Separate bulk notifications for"),
                        elements={
                            "check_type": DictElement(
                                required=False,
                                parameter_form=FixedValue(
                                    title=Title("Check type"),
                                    value=None,
                                ),
                            ),
                            "custom_macro": DictElement(
                                required=False,
                                parameter_form=ListOfStrings(
                                    title=Title("Custom macro"),
                                    layout=ListOfStringsLayout.vertical,
                                    string_spec=String(
                                        field_size=FieldSize.SMALL,
                                    ),
                                ),
                            ),
                            "ec_contact": DictElement(
                                required=False,
                                parameter_form=FixedValue(
                                    title=Title("Event Console contact"),
                                    value=None,
                                ),
                            ),
                            "ec_comment": DictElement(
                                required=False,
                                parameter_form=FixedValue(
                                    title=Title("Event Console comment"),
                                    value=None,
                                ),
                            ),
                            "folder": DictElement(
                                required=False,
                                parameter_form=FixedValue(
                                    title=Title("Folder"),
                                    value=None,
                                ),
                            ),
                            "host": DictElement(
                                required=False,
                                parameter_form=FixedValue(
                                    title=Title("Host"),
                                    value=None,
                                ),
                            ),
                            "state": DictElement(
                                required=False,
                                parameter_form=FixedValue(
                                    title=Title("Host/Service state"),
                                    value=None,
                                ),
                            ),
                            "service": DictElement(
                                required=False,
                                parameter_form=FixedValue(
                                    title=Title("Service name"),
                                    value=None,
                                ),
                            ),
                            "sl": DictElement(
                                required=False,
                                parameter_form=FixedValue(
                                    title=Title("Service level"),
                                    value=None,
                                ),
                            ),
                        },
                    ),
                ),
                "max_notifications": DictElement(
                    required=True,
                    parameter_form=Integer(
                        title=Title("Max. notifications per bulk"),
                        unit_symbol="notifications",
                        prefill=DefaultValue(1000),
                    ),
                ),
                "subject": DictElement(
                    required=True,
                    parameter_form=String(
                        title=Title("Subject line"),
                        field_size=FieldSize.LARGE,
                        prefill=DefaultValue(
                            "Checkmk: $COUNT_NOTIFICATIONS$ notifications for $COUNT_HOSTS$ hosts"
                        ),
                    ),
                ),
                **(
                    {
                        "bulk_outside_timeperiod": DictElement(
                            required=False,
                            parameter_form=DictionaryExtended(
                                title=Title("Bulk outside of the timeperiod"),
                                elements=bulk_notification(title="always").elements,
                            ),
                        )
                    }
                    if title == "timeperiod"
                    else {}
                ),
            },
        )

    def _components() -> Sequence[Widget]:
        return [
            FormSpecWrapper(
                id=FormSpecId("notification_effect"),
                form_spec=DictionaryExtended(
                    layout=DictionaryLayout.two_columns,
                    elements={
                        # TODO: Implement a toggle formspec “Toggle”. It should toggle between two fixed values
                        "notification_effect": DictElement(
                            required=True,
                            parameter_form=String(
                                title=Title("Notification effect"),
                                help_text=Help(
                                    "Specifies whether to send a notification or to cancel all previous notifications for the same method"
                                ),
                                field_size=FieldSize.MEDIUM,
                                prefill=DefaultValue("<placeholder>"),
                                custom_validate=(),
                            ),
                        ),
                        "methods": DictElement(
                            required=True,
                            parameter_form=CascadingSingleChoiceExtended(
                                title=Title("Method"),
                                elements=[
                                    CascadingSingleChoiceElement(
                                        title=Title("%s") % (_("%s") % title),
                                        name=script_name,
                                        parameter_form=SingleChoiceEditable(
                                            title=Title("Notification method"),
                                            entity_type=ConfigEntityType.notification_parameter,
                                            entity_type_specifier=script_name,
                                        ),
                                    )
                                    for script_name, title in notification_script_choices()
                                    if script_name in notification_parameter_registry
                                ],
                                layout=CascadingSingleChoiceLayout.horizontal,
                            ),
                        ),
                        "bulk_notification": DictElement(
                            required=False,
                            parameter_form=CascadingSingleChoiceExtended(
                                title=Title("Bulk Notification"),
                                elements=[
                                    CascadingSingleChoiceElement(
                                        name="always",
                                        title=Title("Always bulk"),
                                        parameter_form=bulk_notification(
                                            title="always",
                                        ),
                                    ),
                                    CascadingSingleChoiceElement(
                                        name="timeperiod",
                                        title=Title("During time period"),
                                        parameter_form=CascadingSingleChoice(
                                            elements=[
                                                CascadingSingleChoiceElement(
                                                    name=timeperiod,
                                                    title=Title("%s") % (_("%s") % timeperiod),
                                                    parameter_form=bulk_notification(
                                                        title="timeperiod",
                                                    ),
                                                )
                                                for timeperiod in load_timeperiods()
                                                if timeperiod != "24X7"
                                            ],
                                        ),
                                    ),
                                ],
                                layout=CascadingSingleChoiceLayout.horizontal,
                            ),
                        ),
                    },
                ),
            ),
        ]

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
                    element_template=CascadingSingleChoiceExtended(
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
                                parameter_form=CascadingSingleChoiceExtended(
                                    help_text=Help(
                                        "Only users who are in all the following contact groups will receive the notification"
                                    ),
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
                                    layout=CascadingSingleChoiceLayout.horizontal,
                                ),
                            ),
                            CascadingSingleChoiceElement(
                                title=Title("Specific users"),
                                name="specific_users",
                                parameter_form=SingleChoiceExtended(
                                    prefill=InputHint(Title("Select user")),
                                    type=str,
                                    elements=[
                                        SingleChoiceElementExtended(
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
                        layout=CascadingSingleChoiceLayout.horizontal,
                    ),
                    add_element_label=Label("Add recipient"),
                    editable_order=False,
                    custom_validate=[
                        not_empty(error_msg=Message("Please add at least one recipient"))
                    ],
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


def _get_time_periods() -> list[tuple[TimeperiodName, str]]:
    return sorted((name, f"{name} - {spec["alias"]}") for name, spec in load_timeperiods().items())


def sending_conditions() -> QuickSetupStage:
    def _components() -> Sequence[Widget]:
        return [
            FormSpecWrapper(
                id=FormSpecId("sending_conditions"),
                form_spec=DictionaryExtended(
                    layout=DictionaryLayout.one_column,
                    elements={
                        "frequency_and_timing": DictElement(
                            required=True,
                            parameter_form=DictionaryExtended(
                                title=Title("Notification frequency and timing"),
                                elements={
                                    "restrict_timeperiod": DictElement(
                                        parameter_form=SingleChoiceExtended(
                                            title=Title("Restrict notifications to a time period"),
                                            type=str,
                                            prefill=InputHint(Title("Select time period")),
                                            elements=[
                                                SingleChoiceElementExtended(
                                                    name=name,
                                                    title=Title(title),  # pylint: disable=localization-of-non-literal-string
                                                )
                                                for name, title in _get_time_periods()
                                            ],
                                        )
                                    ),
                                    "limit_by_count": DictElement(
                                        parameter_form=Tuple(
                                            title=Title("Limit notifications by count to"),
                                            elements=[
                                                Integer(label=Label("between")),
                                                Integer(label=Label("and")),
                                            ],
                                            layout="horizontal",
                                        )
                                    ),
                                    "throttle_periodic": DictElement(
                                        parameter_form=Tuple(
                                            title=Title("Throttling of 'Periodic notifications'"),
                                            help_text=Help(
                                                "Only applies if `Periodic notifications` are enabled"
                                            ),
                                            elements=[
                                                Integer(
                                                    label=Label("starting with notification number")
                                                ),
                                                Integer(
                                                    label=Label("send every"),
                                                    unit_symbol="notifications",
                                                ),
                                            ],
                                            layout="horizontal",
                                        )
                                    ),
                                },
                            ),
                        ),
                        "content_based_filtering": DictElement(
                            required=True,
                            parameter_form=Dictionary(
                                title=Title("Content-based filtering"),
                                elements={
                                    "by_plugin_output": DictElement(
                                        parameter_form=String(
                                            title=Title("By plugin output"),
                                        )
                                    ),
                                    "custom_by_comment": DictElement(
                                        parameter_form=String(
                                            title=Title("'Custom notifications' by comment"),
                                            help_text=Help(
                                                "Only applies to notifications triggered by the command `Custom notifications`"
                                            ),
                                        )
                                    ),
                                },
                            ),
                        ),
                    },
                ),
            )
        ]

    return QuickSetupStage(
        title=_("Sending conditions"),
        sub_title=_(
            "Specify when and how notifications are sent based on frequency, timing, and "
            "content criteria."
        ),
        configure_components=_components,
        custom_validators=[],
        recap=[recaps.recaps_form_spec],
        button_label=_("Next step: General properties"),
    )


def _validate_documentation_url(value: str) -> None:
    if not is_allowed_url(value, cross_domain=True, schemes=["http", "https"]):
        raise ValidationError(
            Message("Not a valid URL (Only http and https URLs are allowed)."),
        )


def general_properties() -> QuickSetupStage:
    def _components() -> Sequence[Widget]:
        return [
            FormSpecWrapper(
                id=FormSpecId("general_properties"),
                form_spec=DictionaryExtended(
                    layout=DictionaryLayout.two_columns,
                    elements={
                        "description": DictElement(
                            required=True,
                            parameter_form=String(
                                title=Title("Description"),
                                field_size=FieldSize.LARGE,
                            ),
                        ),
                        "settings": DictElement(
                            required=True,
                            parameter_form=Dictionary(
                                title=Title("Settings"),
                                elements={
                                    "disable_rule": DictElement(
                                        parameter_form=FixedValue(
                                            title=Title("Disable rule"), value=None
                                        )
                                    ),
                                    "allow_users_to_disable": DictElement(
                                        parameter_form=FixedValue(
                                            title=Title(
                                                "Allow users to deactivate this notification"
                                            ),
                                            value=None,
                                        )
                                    ),
                                },
                            ),
                        ),
                        "comment": DictElement(
                            required=True,
                            parameter_form=CommentTextArea(
                                title=Title("Comment"),
                            ),
                        ),
                        "documentation_url": DictElement(
                            required=True,
                            parameter_form=String(
                                title=Title("Documentation"),
                                field_size=FieldSize.LARGE,
                                custom_validate=(_validate_documentation_url,),
                            ),
                        ),
                    },
                ),
            )
        ]

    return QuickSetupStage(
        title=_("General properties"),
        sub_title=_(
            "Review your notification rule before applying it. They will take effect right "
            'away without "Activate changes".'
        ),
        configure_components=_components,
        custom_validators=[],
        recap=[recaps.recaps_form_spec],
        button_label=_("Next step: Saving"),
    )


def save_and_test_action(
    all_stages_form_data: ParsedFormData, mode: QuickSetupActionMode, object_id: str | None
) -> str:
    match mode:
        case QuickSetupActionMode.SAVE:
            _save(all_stages_form_data)
        case QuickSetupActionMode.EDIT:
            raise NotImplementedError("Edit mode not supported")
        case _:
            raise ValueError(f"Unknown mode {mode}")
    return mode_url("test_notifications", result=_("New notification rule successfully created!"))


def save_and_new_action(
    all_stages_form_data: ParsedFormData, mode: QuickSetupActionMode, object_id: str | None
) -> str:
    match mode:
        case QuickSetupActionMode.SAVE:
            _save(all_stages_form_data)
        case QuickSetupActionMode.EDIT:
            raise NotImplementedError("Edit mode not yet supported")
        case _:
            raise ValueError(f"Unknown mode {mode}")
    return mode_url(
        "notification_rule_quick_setup", result=_("New notification rule successfully created!")
    )


def register(quick_setup_registry: QuickSetupRegistry) -> None:
    quick_setup_registry.register(quick_setup_notifications)


def _save(all_stages_form_data: ParsedFormData) -> None:
    config_file = NotificationRuleConfigFile()
    notifications_rules = list(config_file.load_for_modification())
    notifications_rules += [
        migrate_to_event_rule(cast(NotificationQuickSetupSpec, all_stages_form_data))
    ]
    config_file.save(notifications_rules)


def load_notifications(object_id: str) -> ParsedFormData:
    config_file = NotificationRuleConfigFile()
    notifications_rules = list(config_file.load_for_reading())
    for rule in notifications_rules:
        if rule["rule_id"] == object_id:
            return cast(ParsedFormData, migrate_to_notification_quick_setup_spec(rule))
    return {}


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
    actions=[
        QuickSetupAction(
            id="apply_and_test",
            label=_("Apply & test notification rule"),
            action=save_and_test_action,
        ),
        QuickSetupAction(
            id="apply_and_create_new",
            label=_("Apply & create another rule"),
            action=save_and_new_action,
        ),
    ],
    load_data=load_notifications,
)
