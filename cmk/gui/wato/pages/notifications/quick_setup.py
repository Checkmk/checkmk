#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence
from typing import Any, assert_never, cast, Literal

from cmk.utils.tags import AuxTag, TagGroup
from cmk.utils.timeperiod import TimeperiodName
from cmk.utils.user import UserId

from cmk.gui.config import active_config
from cmk.gui.form_specs.converter import Tuple
from cmk.gui.form_specs.private import (
    CascadingSingleChoiceExtended,
    CommentTextArea,
    ConditionChoices,
    DictionaryExtended,
    Labels,
    ListExtended,
    ListOfStrings,
    ListUniqueSelection,
    MultipleChoiceExtended,
    MultipleChoiceExtendedLayout,
    not_empty,
    SingleChoiceEditable,
    SingleChoiceElementExtended,
    SingleChoiceExtended,
    StringAutocompleter,
    World,
)
from cmk.gui.form_specs.private.cascading_single_choice_extended import (
    CascadingSingleChoiceElementExtended,
)
from cmk.gui.form_specs.private.list_unique_selection import (
    UniqueCascadingSingleChoiceElement,
    UniqueSingleChoiceElement,
)
from cmk.gui.form_specs.private.multiple_choice import MultipleChoiceElementExtended
from cmk.gui.hooks import request_memoize
from cmk.gui.i18n import _
from cmk.gui.mkeventd import service_levels, syslog_facilities, syslog_priorities
from cmk.gui.quick_setup.private.widgets import (
    ConditionalNotificationECAlertStageWidget,
    ConditionalNotificationServiceEventStageWidget,
)
from cmk.gui.quick_setup.v0_unstable._registry import QuickSetupRegistry
from cmk.gui.quick_setup.v0_unstable.predefined import recaps
from cmk.gui.quick_setup.v0_unstable.setups import (
    QuickSetup,
    QuickSetupAction,
    QuickSetupActionMode,
    QuickSetupStage,
    QuickSetupStageAction,
)
from cmk.gui.quick_setup.v0_unstable.type_defs import (
    ActionId,
    GeneralStageErrors,
    ParsedFormData,
    QuickSetupId,
    StageIndex,
)
from cmk.gui.quick_setup.v0_unstable.widgets import (
    Collapsible,
    FormSpecId,
    FormSpecWrapper,
    Widget,
)
from cmk.gui.user_sites import get_activation_site_choices
from cmk.gui.userdb import load_users
from cmk.gui.wato._group_selection import sorted_contact_group_choices
from cmk.gui.wato.pages.notifications.migrate import (
    migrate_to_event_rule,
    migrate_to_notification_quick_setup_spec,
)
from cmk.gui.wato.pages.notifications.quick_setup_types import (
    NotificationQuickSetupSpec,
)
from cmk.gui.watolib.groups_io import (
    load_host_group_information,
    load_service_group_information,
)
from cmk.gui.watolib.hosts_and_folders import folder_tree
from cmk.gui.watolib.mode import mode_url
from cmk.gui.watolib.notifications import NotificationRuleConfigFile
from cmk.gui.watolib.timeperiods import load_timeperiods
from cmk.gui.watolib.user_scripts import load_notification_scripts
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
from cmk.rulesets.v1.form_specs.validators import (
    EmailAddress,
    LengthInRange,
    NumberInRange,
    Url,
    UrlProtocol,
    ValidationError,
)
from cmk.shared_typing.configuration_entity import ConfigEntityType
from cmk.shared_typing.vue_formspec_components import (
    Autocompleter,
    AutocompleterData,
    AutocompleterParams,
    CascadingSingleChoiceLayout,
    Condition,
    ConditionGroup,
    DictionaryLayout,
    ListOfStringsLayout,
)

NEXT_BUTTON_ARIA_LABEL = _("Go to the next stage")
PREV_BUTTON_ARIA_LABEL = _("Go to the previous stage")
PREV_BUTTON_LABEL = _("Back")


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


def _event_choices(
    what: Literal["host", "service"],
) -> Sequence[UniqueCascadingSingleChoiceElement]:
    return [
        UniqueCascadingSingleChoiceElement(
            unique=False,
            parameter_form=CascadingSingleChoiceElementExtended(
                name="status_change",
                title=Title("Status change"),
                parameter_form=Tuple(
                    layout="horizontal",
                    elements=[
                        SingleChoiceExtended(
                            label=Label("From"),
                            prefill=DefaultValue(-1),
                            elements=[
                                SingleChoiceElementExtended(name=state, title=title)
                                for state, title in _get_states(what)
                            ],
                        ),
                        SingleChoiceExtended(
                            label=Label("to"),
                            prefill=DefaultValue(1) if what == "host" else DefaultValue(2),
                            elements=[
                                SingleChoiceElementExtended(name=state, title=title)
                                for state, title in _get_states(what)
                            ],
                        ),
                    ],
                    custom_validate=[_validate_from_to],
                ),
            ),
        ),
        UniqueCascadingSingleChoiceElement(
            parameter_form=CascadingSingleChoiceElementExtended(
                name="downtime",
                title=Title("Start or end of downtime"),
                parameter_form=FixedValue(value=None),
            ),
        ),
        UniqueCascadingSingleChoiceElement(
            parameter_form=CascadingSingleChoiceElementExtended(
                name="acknowledgement",
                title=Title("Acknowledgement of problem"),
                parameter_form=FixedValue(value=None),
            ),
        ),
        UniqueCascadingSingleChoiceElement(
            parameter_form=CascadingSingleChoiceElementExtended(
                name="flapping_state",
                title=Title("Start or end of flapping state"),
                parameter_form=FixedValue(value=None),
            ),
        ),
        UniqueCascadingSingleChoiceElement(
            unique=False,
            parameter_form=CascadingSingleChoiceElementExtended(
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
        ),
    ]


# TODO maybe introduce a real validator
def _validate_from_to(p):
    if p[0] == p[1]:
        raise ValidationError(
            Message("Source state can not be equal to target state."),
        )


def _validate_at_least_one_event(
    _quick_setup_id: QuickSetupId,
    form_data: ParsedFormData,
) -> GeneralStageErrors:
    match form_data[FormSpecId("triggering_events")]:
        case ("specific_events", data):
            if not data:
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
                form_spec=CascadingSingleChoiceExtended(
                    prefill=DefaultValue("specific_events"),
                    layout=CascadingSingleChoiceLayout.button_group,
                    elements=[
                        CascadingSingleChoiceElement(
                            name="specific_events",
                            title=Title("Specific events"),
                            parameter_form=DictionaryExtended(
                                layout=DictionaryLayout.two_columns,
                                prefill=DefaultValue(
                                    {
                                        "host_events": [
                                            ("status_change", (-1, HostState.DOWN)),
                                            ("status_change", (-1, HostState.UP)),
                                        ],
                                        "service_events": [
                                            ("status_change", (-1, ServiceState.CRIT)),
                                            ("status_change", (-1, ServiceState.WARN)),
                                            ("status_change", (-1, ServiceState.OK)),
                                        ],
                                    }
                                ),
                                elements={
                                    "host_events": DictElement(
                                        parameter_form=ListUniqueSelection(
                                            title=Title("Host events"),
                                            prefill=DefaultValue([]),
                                            single_choice_type=CascadingSingleChoice,
                                            cascading_single_choice_layout=CascadingSingleChoiceLayout.horizontal,
                                            elements=_event_choices("host"),
                                            add_element_label=Label("Add event"),
                                            custom_validate=[_validate_empty_selection],
                                        )
                                    ),
                                    "service_events": DictElement(
                                        parameter_form=ListUniqueSelection(
                                            title=Title("Service events"),
                                            prefill=DefaultValue([]),
                                            single_choice_type=CascadingSingleChoice,
                                            cascading_single_choice_layout=CascadingSingleChoiceLayout.horizontal,
                                            elements=_event_choices("service"),
                                            add_element_label=Label("Add event"),
                                            custom_validate=[_validate_empty_selection],
                                        )
                                    ),
                                    "ec_alerts": DictElement(
                                        parameter_form=FixedValue(
                                            title=Title("Event Console alerts"),
                                            label=Label("Enabled"),
                                            value=True,
                                        ),
                                    ),
                                },
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="all_events",
                            title=Title("All events"),
                            parameter_form=FixedValue(
                                value=None,
                                label=Label(
                                    "All host events, service events and event console alerts will "
                                    "trigger a notification"
                                ),
                            ),
                        ),
                    ],
                ),
            )
        ]

    return QuickSetupStage(
        title=_("Triggering events"),
        sub_title=_("Define any events you want to be notified about."),
        configure_components=_components,
        actions=[
            QuickSetupStageAction(
                id=ActionId("action"),
                custom_validators=[_validate_at_least_one_event],
                recap=[custom_recap_formspec_triggering_events],
                next_button_label=_("Next step: Specify host/services"),
            ),
        ],
    )


def custom_recap_formspec_triggering_events(
    quick_setup_id: QuickSetupId,
    stage_index: StageIndex,
    all_stages_form_data: ParsedFormData,
) -> Sequence[Widget]:
    cleaned_stages_form_data = {
        form_spec_wrapper_id: (
            mode,
            {
                form_spec_id: data
                for form_spec_id, data in form_data.items()
                if form_spec_id not in ["host_events", "service_events"] or len(data) > 0
            }
            if isinstance(form_data, dict)
            else form_data,
        )
        for form_spec_wrapper_id, (mode, form_data) in all_stages_form_data.items()
    }
    return recaps.recaps_form_spec(quick_setup_id, stage_index, cleaned_stages_form_data)


def _validate_empty_selection(selections: Sequence[Sequence[str | None]]) -> None:
    # TODO validation seems not to be possible for a single empty element of
    # the Tuple
    if ["", None] in selections:
        raise ValidationError(
            Message("At least one selection is missing."),
        )


def _get_contact_group_users() -> list[tuple[UserId, str]]:
    return sorted(
        (name, f"{name} - {user.get('alias', name)}")
        for name, user in load_users().items()
        if user.get("contactgroups")
    )


def _get_service_levels_single_choice() -> Sequence[SingleChoiceElementExtended]:
    return [
        SingleChoiceElementExtended(
            name=name,
            title=Title("%s") % _(" %s") % title,
        )
        for name, title in service_levels()
    ]


@request_memoize()
def _get_cached_tags() -> Sequence[TagGroup | AuxTag]:
    choices: list[TagGroup | AuxTag] = []
    all_topics = active_config.tags.get_topic_choices()
    tag_groups_by_topic = dict(active_config.tags.get_tag_groups_by_topic())
    aux_tags_by_topic = dict(active_config.tags.get_aux_tags_by_topic())
    for topic_id, _topic_title in all_topics:
        for tag_group in tag_groups_by_topic.get(topic_id, []):
            choices.append(tag_group)

        for aux_tag in aux_tags_by_topic.get(topic_id, []):
            choices.append(aux_tag)

    return choices


def _get_condition_choices() -> dict[str, ConditionGroup]:
    choices: dict[str, ConditionGroup] = {}
    for tag in _get_cached_tags():
        match tag:
            case TagGroup():
                choices[tag.id] = ConditionGroup(
                    title=tag.choice_title,
                    conditions=[Condition(name=t.id or "", title=t.title) for t in tag.tags],
                )
            case AuxTag():
                choices[tag.id] = ConditionGroup(
                    title=tag.choice_title,
                    conditions=[Condition(name=tag.id, title=tag.title)],
                )
            case other:
                assert_never(other)
    return choices


def custom_recap_formspec_filter_for_hosts_and_services(
    quick_setup_id: QuickSetupId,
    stage_index: StageIndex,
    all_stages_form_data: ParsedFormData,
) -> Sequence[Widget]:
    cleaned_stages_form_data = {
        form_spec_wrapper_id: form_data
        for form_spec_wrapper_id, form_data in all_stages_form_data.items()
        if len(form_data) > 0
    }
    return recaps.recaps_form_spec(quick_setup_id, stage_index, cleaned_stages_form_data)


def filter_for_hosts_and_services() -> QuickSetupStage:
    def _components() -> Sequence[Widget]:
        return [
            ConditionalNotificationECAlertStageWidget(
                items=[
                    Collapsible(
                        title=_("Event Console alert filters"),
                        items=[
                            FormSpecWrapper(
                                id=FormSpecId("ec_alert_filters"),
                                form_spec=DictionaryExtended(
                                    layout=DictionaryLayout.two_columns,
                                    elements={
                                        "rule_ids": DictElement(
                                            parameter_form=ListExtended(
                                                title=Title("Rule IDs"),
                                                element_template=String(
                                                    field_size=FieldSize.SMALL,
                                                ),
                                                editable_order=False,
                                                prefill=DefaultValue([]),
                                            ),
                                        ),
                                        "syslog_priority": DictElement(
                                            parameter_form=Tuple(
                                                title=Title("Syslog priority"),
                                                elements=[
                                                    SingleChoiceExtended(
                                                        title=Title("from:"),
                                                        elements=[
                                                            SingleChoiceElementExtended(
                                                                name=name,
                                                                title=Title("%s") % title,
                                                            )
                                                            for name, title in syslog_priorities
                                                        ],
                                                    ),
                                                    SingleChoiceExtended(
                                                        title=Title("to:"),
                                                        elements=[
                                                            SingleChoiceElementExtended(
                                                                name=name,
                                                                title=Title("%s") % title,
                                                            )
                                                            for name, title in syslog_priorities
                                                        ],
                                                    ),
                                                ],
                                                layout="horizontal",
                                            )
                                        ),
                                        "syslog_facility": DictElement(
                                            parameter_form=SingleChoiceExtended(
                                                title=Title("Syslog facility"),
                                                elements=[
                                                    SingleChoiceElementExtended(
                                                        name=name,
                                                        title=Title("%s") % title,
                                                    )
                                                    for name, title in syslog_facilities
                                                ],
                                            ),
                                        ),
                                        "event_comment": DictElement(
                                            parameter_form=String(
                                                title=Title("Event comment"),
                                                field_size=FieldSize.LARGE,
                                            ),
                                        ),
                                    },
                                ),
                            )
                        ],
                    )
                ],
            ),
            Collapsible(
                title=_("Host filters"),
                items=[
                    FormSpecWrapper(
                        id=FormSpecId("host_filters"),
                        form_spec=DictionaryExtended(
                            layout=DictionaryLayout.two_columns,
                            elements={
                                "host_tags": DictElement(
                                    parameter_form=ConditionChoices(
                                        title=Title("Host tags"),
                                        add_condition_group_label=Label("Add tag condition"),
                                        select_condition_group_to_add=Label("Select tag to add"),
                                        no_more_condition_groups_to_add=Label(
                                            "No more tags to add"
                                        ),
                                        get_conditions=_get_condition_choices,
                                        custom_validate=[
                                            not_empty(
                                                error_msg=Message(
                                                    "Please add at least one tag condition."
                                                )
                                            )
                                        ],
                                    ),
                                ),
                                "host_labels": DictElement(
                                    parameter_form=Labels(
                                        title=Title("Host labels"),
                                        help_text=Help(
                                            "Use this condition to select hosts based on the configured host labels."
                                        ),
                                        world=World.CORE,
                                    )
                                ),
                                "match_host_groups": DictElement(
                                    parameter_form=MultipleChoiceExtended(
                                        title=Title("Host groups"),
                                        elements=[
                                            MultipleChoiceElementExtended(
                                                name=group_name,
                                                title=Title("%s") % group_name,
                                            )
                                            for group_name in load_host_group_information().keys()
                                        ],
                                        show_toggle_all=True,
                                        layout=MultipleChoiceExtendedLayout.dual_list,
                                    ),
                                ),
                                "match_hosts": DictElement(
                                    parameter_form=ListOfStrings(
                                        title=Title("Hosts"),
                                        string_spec=StringAutocompleter(
                                            autocompleter=Autocompleter(
                                                data=AutocompleterData(
                                                    ident="config_hostname",
                                                    params=AutocompleterParams(),
                                                ),
                                            ),
                                        ),
                                    ),
                                ),
                                "exclude_hosts": DictElement(
                                    parameter_form=ListOfStrings(
                                        title=Title("Exclude hosts"),
                                        string_spec=StringAutocompleter(
                                            autocompleter=Autocompleter(
                                                data=AutocompleterData(
                                                    ident="config_hostname",
                                                    params=AutocompleterParams(),
                                                ),
                                            ),
                                        ),
                                    ),
                                ),
                            },
                        ),
                    )
                ],
            ),
            ConditionalNotificationServiceEventStageWidget(
                items=[
                    Collapsible(
                        title=_("Service filters"),
                        items=[
                            FormSpecWrapper(
                                id=FormSpecId("service_filters"),
                                form_spec=DictionaryExtended(
                                    layout=DictionaryLayout.two_columns,
                                    elements={
                                        "service_labels": DictElement(
                                            parameter_form=Labels(
                                                title=Title("Service labels"),
                                                help_text=Help(
                                                    "Use this condition to select services based on the configured service labels."
                                                ),
                                                world=World.CORE,
                                            )
                                        ),
                                        "match_service_groups": DictElement(
                                            parameter_form=MultipleChoiceExtended(
                                                title=Title("Service groups"),
                                                elements=[
                                                    MultipleChoiceElementExtended(
                                                        name=group_name,
                                                        title=Title("%s") % group_name,
                                                    )
                                                    for group_name in load_service_group_information().keys()
                                                ],
                                                show_toggle_all=True,
                                                layout=MultipleChoiceExtendedLayout.dual_list,
                                            ),
                                        ),
                                        "exclude_service_groups": DictElement(
                                            parameter_form=MultipleChoiceExtended(
                                                title=Title("Exclude service groups"),
                                                elements=[
                                                    MultipleChoiceElementExtended(
                                                        name=group_name,
                                                        title=Title("%s") % group_name,
                                                    )
                                                    for group_name in load_service_group_information().keys()
                                                ],
                                                show_toggle_all=True,
                                                layout=MultipleChoiceExtendedLayout.dual_list,
                                            ),
                                        ),
                                        "match_services": DictElement(
                                            parameter_form=ListOfStrings(
                                                title=Title("Services"),
                                                string_spec=String(
                                                    field_size=FieldSize.MEDIUM,
                                                ),
                                            ),
                                        ),
                                        "exclude_services": DictElement(
                                            parameter_form=ListOfStrings(
                                                title=Title("Exclude services"),
                                                string_spec=String(
                                                    field_size=FieldSize.MEDIUM,
                                                ),
                                            ),
                                        ),
                                    },
                                ),
                            )
                        ],
                    ),
                ],
            ),
            Collapsible(
                title=_("Contact group filters"),
                help_text=_(
                    "Not the recipient, but filters hosts and services assigned "
                    "to a contact group or members of a contact group",
                ),
                items=[
                    FormSpecWrapper(
                        id=FormSpecId("assignee_filters"),
                        form_spec=DictionaryExtended(
                            layout=DictionaryLayout.two_columns,
                            elements={
                                "contact_groups": DictElement(
                                    parameter_form=MultipleChoiceExtended(
                                        title=Title("Groups"),
                                        elements=[
                                            MultipleChoiceElementExtended(
                                                name=name,
                                                title=Title("%s") % title,
                                            )
                                            for name, title in sorted_contact_group_choices()
                                        ],
                                        show_toggle_all=True,
                                        layout=MultipleChoiceExtendedLayout.dual_list,
                                    ),
                                ),
                                "users": DictElement(
                                    parameter_form=ListExtended(
                                        title=Title("Members"),
                                        editable_order=False,
                                        help_text=Help(
                                            "Filters for hosts or services that "
                                            "have at least one of the contact "
                                            "group members assigned to them."
                                        ),
                                        element_template=SingleChoiceExtended(
                                            prefill=InputHint(Title("Select user")),
                                            no_elements_text=Message(  # TODO:  Doesn't seem to do anything.
                                                "No users available"
                                            ),
                                            elements=[
                                                SingleChoiceElementExtended(
                                                    name=userid,
                                                    title=Title("%s") % user,
                                                )
                                                for userid, user in _get_contact_group_users()
                                            ],
                                        ),
                                        prefill=DefaultValue([]),
                                    ),
                                ),
                            },
                        ),
                    ),
                ],
            ),
            Collapsible(
                title="General filters",
                items=[
                    FormSpecWrapper(
                        id=FormSpecId("general_filters"),
                        form_spec=DictionaryExtended(
                            layout=DictionaryLayout.two_columns,
                            elements={
                                "service_level": DictElement(
                                    parameter_form=CascadingSingleChoiceExtended(
                                        prefill=DefaultValue("explicit"),
                                        layout=CascadingSingleChoiceLayout.button_group,
                                        help_text=Help(
                                            "Describes the business impact of a host or service"
                                        ),
                                        title=Title("Service level"),
                                        elements=[
                                            CascadingSingleChoiceElement(
                                                name="explicit",
                                                title=Title("Explicit"),
                                                parameter_form=SingleChoiceExtended(
                                                    elements=_get_service_levels_single_choice(),
                                                ),
                                            ),
                                            CascadingSingleChoiceElement(
                                                name="range",
                                                title=Title("Range"),
                                                parameter_form=Tuple(
                                                    title=Title("Service level"),
                                                    elements=[
                                                        SingleChoiceExtended(
                                                            title=Title("From:"),
                                                            elements=_get_service_levels_single_choice(),
                                                        ),
                                                        SingleChoiceExtended(
                                                            title=Title("to:"),
                                                            elements=_get_service_levels_single_choice(),
                                                        ),
                                                    ],
                                                    layout="horizontal",
                                                ),
                                            ),
                                        ],
                                    ),
                                ),
                                "folder": DictElement(
                                    parameter_form=SingleChoiceExtended(
                                        title=Title("Folder"),
                                        elements=[
                                            SingleChoiceElementExtended(
                                                name=name,
                                                title=Title("%s") % _(" %s") % folder,
                                            )
                                            for name, folder in folder_tree().folder_choices()
                                        ],
                                    ),
                                ),
                                "sites": DictElement(
                                    parameter_form=MultipleChoiceExtended(
                                        title=Title("Sites"),
                                        elements=[
                                            MultipleChoiceElementExtended(
                                                name=name,
                                                title=Title("%s") % title,
                                            )
                                            for name, title in get_activation_site_choices()
                                        ],
                                        show_toggle_all=True,
                                        layout=MultipleChoiceExtendedLayout.dual_list,
                                    ),
                                ),
                                "check_type_plugin": DictElement(
                                    parameter_form=MultipleChoiceExtended(
                                        title=Title("Check types"),
                                        elements=Autocompleter(
                                            data=AutocompleterData(
                                                ident="check_types",
                                                params=AutocompleterParams(),
                                            ),
                                        ),
                                        show_toggle_all=True,
                                        layout=MultipleChoiceExtendedLayout.dual_list,
                                    ),
                                ),
                            },
                        ),
                    ),
                ],
            ),
        ]

    return QuickSetupStage(
        title=_("Filter for hosts/services"),
        sub_title=_(
            "Apply filters to specify which hosts and services are affected by this "
            "notification rule."
        ),
        configure_components=_components,
        actions=[
            QuickSetupStageAction(
                id=ActionId("action"),
                custom_validators=[],
                recap=[custom_recap_formspec_filter_for_hosts_and_services],
                next_button_label=_("Next step: Notification method (plug-in)"),
            )
        ],
        prev_button_label=PREV_BUTTON_LABEL,
    )


def supports_bulk(script_name: str, notification_scripts: dict[str, Any]) -> bool:
    if script_name not in notification_scripts:
        return False
    return notification_scripts[script_name].get("bulk", False)


def notification_method() -> QuickSetupStage:
    def bulk_notification_dict_element() -> DictElement:
        return DictElement(
            required=False,
            parameter_form=CascadingSingleChoiceExtended(
                title=Title("Bulk notification"),
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
                        parameter_form=CascadingSingleChoiceExtended(
                            elements=[
                                CascadingSingleChoiceElementExtended(
                                    name=name,
                                    title=Title("%s") % (_("%s") % timeperiod),
                                    parameter_form=bulk_notification(
                                        title="timeperiod",
                                    ),
                                )
                                for name, timeperiod in _get_time_periods()
                            ],
                        ),
                    ),
                ],
                layout=CascadingSingleChoiceLayout.vertical,
                prefill=DefaultValue("always"),
            ),
        )

    def bulk_notification_supported(
        script_name: str, notification_scripts: dict[str, Any]
    ) -> dict[str, DictElement]:
        if not supports_bulk(script_name, notification_scripts):
            return {}
        return {
            "bulk_notification": bulk_notification_dict_element(),
        }

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
                        custom_validate=[NumberInRange(min_value=2, max_value=1000)],
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
        notification_scripts = load_notification_scripts()

        return [
            FormSpecWrapper(
                id=FormSpecId("notification_method"),
                form_spec=DictionaryExtended(
                    layout=DictionaryLayout.two_columns,
                    elements={
                        "notification_effect": DictElement(
                            required=True,
                            parameter_form=CascadingSingleChoiceExtended(
                                prefill=DefaultValue("send"),
                                layout=CascadingSingleChoiceLayout.button_group,
                                title=Title("Notification effect"),
                                help_text=Help(
                                    "Specifies whether to send a notification or to cancel all previous notifications for the same method"
                                ),
                                elements=[
                                    CascadingSingleChoiceElement(
                                        name="send",
                                        title=Title("Send notification"),
                                        parameter_form=CascadingSingleChoiceExtended(
                                            title=Title("Method"),
                                            elements=[
                                                CascadingSingleChoiceElementExtended(
                                                    title=Title("%s") % (_("%s") % title),
                                                    name=script_name,
                                                    parameter_form=Dictionary(
                                                        elements={
                                                            "parameter_id": DictElement(
                                                                required=True,
                                                                parameter_form=SingleChoiceEditable(
                                                                    title=Title(
                                                                        "Select parameters"
                                                                    ),
                                                                    help_text=Help(
                                                                        "Parameters define the look, content, "
                                                                        "and connection details of the notification and are reusable."
                                                                    ),
                                                                    entity_type=ConfigEntityType.notification_parameter,
                                                                    entity_type_specifier=script_name,
                                                                ),
                                                            ),
                                                        }
                                                        | bulk_notification_supported(
                                                            script_name,
                                                            notification_scripts,
                                                        )
                                                    ),
                                                )
                                                for script_name, title in notification_script_choices()
                                            ],
                                            custom_validate=[_validate_parameter_choice],
                                            layout=CascadingSingleChoiceLayout.vertical,
                                            prefill=DefaultValue("mail"),
                                        ),
                                    ),
                                    CascadingSingleChoiceElement(
                                        name="suppress",
                                        title=Title("Suppress all previous"),
                                        parameter_form=CascadingSingleChoiceExtended(
                                            title=Title("Method"),
                                            elements=[
                                                CascadingSingleChoiceElementExtended(
                                                    title=Title("%s") % (_("%s") % title),
                                                    name=script_name,
                                                    parameter_form=FixedValue(value=None),
                                                )
                                                for script_name, title in notification_script_choices()
                                            ],
                                        ),
                                    ),
                                ],
                            ),
                        ),
                    },
                ),
            ),
        ]

    return QuickSetupStage(
        title=_("Notification method (plug-in)"),
        sub_title=_("What should be sent out?"),
        configure_components=_components,
        actions=[
            QuickSetupStageAction(
                id=ActionId("action"),
                custom_validators=[],
                recap=[recaps.recaps_form_spec],
                next_button_label=_("Next step: Recipient"),
            )
        ],
        prev_button_label=PREV_BUTTON_LABEL,
    )


def _validate_parameter_choice(script_config: tuple[str, object]) -> None:
    parameter_choice = script_config[1]
    assert isinstance(parameter_choice, dict)
    if parameter_choice.get("parameter_id") is None:
        raise ValidationError(
            Message("Please choose a notification parameter or create one."),
        )


def _get_sorted_users() -> list[tuple[UserId, str]]:
    return sorted(
        (name, f"{name} - {user.get("alias", name)}") for name, user in load_users().items()
    )


def _contact_group_choice() -> Sequence[UniqueSingleChoiceElement]:
    return [
        UniqueSingleChoiceElement(
            parameter_form=SingleChoiceElementExtended(
                name=ident,
                title=Title(title),  # pylint: disable=localization-of-non-literal-string
            ),
        )
        for ident, title in sorted_contact_group_choices()
    ]


def recipient() -> QuickSetupStage:
    def _components() -> Sequence[Widget]:
        return [
            FormSpecWrapper(
                id=FormSpecId("recipient"),
                form_spec=DictionaryExtended(
                    elements={
                        "receive": DictElement(
                            required=True,
                            parameter_form=ListUniqueSelection(
                                title=Title("Select recipient"),
                                prefill=DefaultValue([("all_contacts_affected", None)]),
                                single_choice_type=CascadingSingleChoice,
                                cascading_single_choice_layout=CascadingSingleChoiceLayout.horizontal,
                                elements=[
                                    UniqueCascadingSingleChoiceElement(
                                        parameter_form=CascadingSingleChoiceElementExtended(
                                            title=Title("All contacts of the affected object"),
                                            name="all_contacts_affected",
                                            parameter_form=FixedValue(value=None),
                                        ),
                                    ),
                                    UniqueCascadingSingleChoiceElement(
                                        parameter_form=CascadingSingleChoiceElementExtended(
                                            title=Title("All users with an email address"),
                                            name="all_email_users",
                                            parameter_form=FixedValue(value=None),
                                        ),
                                    ),
                                    UniqueCascadingSingleChoiceElement(
                                        parameter_form=CascadingSingleChoiceElementExtended(
                                            title=Title("Contact group"),
                                            name="contact_group",
                                            parameter_form=ListUniqueSelection(
                                                prefill=DefaultValue([]),
                                                single_choice_prefill=InputHint(
                                                    Title("Select contact group")
                                                ),
                                                single_choice_type=SingleChoice,
                                                elements=_contact_group_choice(),
                                                custom_validate=[
                                                    LengthInRange(
                                                        min_value=1,
                                                        error_msg=Message(
                                                            "Please add at least one contact group"
                                                        ),
                                                    )
                                                ],
                                            ),
                                        ),
                                    ),
                                    UniqueCascadingSingleChoiceElement(
                                        parameter_form=CascadingSingleChoiceElementExtended(
                                            title=Title("Explicit email addresses"),
                                            name="explicit_email_addresses",
                                            parameter_form=ListOfStrings(
                                                layout=ListOfStringsLayout.vertical,
                                                string_spec=String(
                                                    custom_validate=[EmailAddress()],
                                                ),
                                                custom_validate=[
                                                    LengthInRange(
                                                        min_value=1,
                                                        error_msg=Message(
                                                            "Please add at least one email address"
                                                        ),
                                                    ),
                                                ],
                                            ),
                                        ),
                                    ),
                                    UniqueCascadingSingleChoiceElement(
                                        parameter_form=CascadingSingleChoiceElementExtended(
                                            title=Title("Specific users"),
                                            name="specific_users",
                                            parameter_form=ListUniqueSelection(
                                                prefill=DefaultValue([]),
                                                single_choice_prefill=InputHint(
                                                    Title("Select user")
                                                ),
                                                single_choice_type=SingleChoice,
                                                elements=[
                                                    UniqueSingleChoiceElement(
                                                        parameter_form=SingleChoiceElementExtended(
                                                            name=ident,
                                                            title=Title(title),  # pylint: disable=localization-of-non-literal-string
                                                        )
                                                    )
                                                    for ident, title in _get_sorted_users()
                                                ],
                                                custom_validate=[
                                                    LengthInRange(
                                                        min_value=1,
                                                        error_msg=Message(
                                                            "Please add at least one user"
                                                        ),
                                                    ),
                                                ],
                                            ),
                                        ),
                                    ),
                                    UniqueCascadingSingleChoiceElement(
                                        parameter_form=CascadingSingleChoiceElementExtended(
                                            title=Title("All users"),
                                            name="all_users",
                                            parameter_form=FixedValue(value=None),
                                        ),
                                    ),
                                ],
                                add_element_label=Label("Add recipient"),
                                custom_validate=[
                                    not_empty(
                                        error_msg=Message("Please add at least one recipient")
                                    )
                                ],
                            ),
                        ),
                        "restrict_previous": DictElement(
                            required=False,
                            parameter_form=ListUniqueSelection(
                                title=Title("Restrict previous options to"),
                                prefill=DefaultValue([]),
                                add_element_label=Label("Add restriction"),
                                cascading_single_choice_layout=CascadingSingleChoiceLayout.horizontal,
                                single_choice_type=CascadingSingleChoice,
                                elements=[
                                    UniqueCascadingSingleChoiceElement(
                                        parameter_form=CascadingSingleChoiceElementExtended(
                                            name="contact_group",
                                            title=Title("Users of contact groups"),
                                            parameter_form=ListUniqueSelection(
                                                prefill=DefaultValue([]),
                                                single_choice_prefill=InputHint(
                                                    Title("Select contact group")
                                                ),
                                                single_choice_type=SingleChoice,
                                                elements=_contact_group_choice(),
                                                custom_validate=[
                                                    LengthInRange(
                                                        min_value=1,
                                                        error_msg=Message(
                                                            "Please add at least one contact group"
                                                        ),
                                                    ),
                                                ],
                                            ),
                                        ),
                                    ),
                                    UniqueCascadingSingleChoiceElement(
                                        parameter_form=CascadingSingleChoiceElementExtended(
                                            name="custom_macro",
                                            title=Title("Custom macros"),
                                            parameter_form=ListExtended(
                                                prefill=DefaultValue([]),
                                                editable_order=False,
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
                                                custom_validate=[
                                                    LengthInRange(
                                                        min_value=1,
                                                        error_msg=Message(
                                                            "Please add at least one macro"
                                                        ),
                                                    ),
                                                ],
                                            ),
                                        ),
                                    ),
                                ],
                            ),
                        ),
                    }
                ),
            )
        ]

    return QuickSetupStage(
        title=_("Recipient"),
        sub_title=_("Who should receive the notification?"),
        configure_components=_components,
        actions=[
            QuickSetupStageAction(
                id=ActionId("action"),
                custom_validators=[],
                recap=[recaps.recaps_form_spec],
                next_button_label=_("Next step: Sending conditions"),
            )
        ],
        prev_button_label=PREV_BUTTON_LABEL,
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
                                                Integer(
                                                    label=Label("between"),
                                                    prefill=DefaultValue(5),
                                                ),
                                                Integer(
                                                    label=Label("and"),
                                                    prefill=DefaultValue(100),
                                                ),
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
                                                    label=Label(
                                                        "Starting with notification number"
                                                    ),
                                                    prefill=DefaultValue(10),
                                                ),
                                                Integer(
                                                    label=Label("send every"),
                                                    prefill=DefaultValue(5),
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
                                            custom_validate=[
                                                not_empty(
                                                    error_msg=Message(
                                                        "Enter a plugin output to define what to filter for."
                                                    )
                                                )
                                            ],
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
        actions=[
            QuickSetupStageAction(
                id=ActionId("action"),
                custom_validators=[],
                recap=[recaps.recaps_form_spec],
                next_button_label=_("Next step: General properties"),
            )
        ],
        prev_button_label=PREV_BUTTON_LABEL,
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
                                title=Title("Documentation URL"),
                                field_size=FieldSize.LARGE,
                                custom_validate=[_validate_optional_url],
                            ),
                        ),
                    },
                ),
            )
        ]

    return QuickSetupStage(
        title=_("General properties"),
        sub_title=_(
            "Make your rule more recognizable with a meaningful description and other metadata. "
            'Note: Notification rules take effect immediately without "Activate changes".'
        ),
        configure_components=_components,
        actions=[
            QuickSetupStageAction(
                id=ActionId("action"),
                custom_validators=[],
                recap=[recaps.recaps_form_spec],
                next_button_label=_("Next step: Review all settings"),
            )
        ],
        prev_button_label=PREV_BUTTON_LABEL,
    )


def _validate_optional_url(value: str) -> None:
    if not value:
        return

    url_validator_instance = Url(protocols=[UrlProtocol.HTTP, UrlProtocol.HTTPS])
    url_validator_instance(value)


def save_and_test_action(
    all_stages_form_data: ParsedFormData, mode: QuickSetupActionMode, object_id: str | None
) -> str:
    match mode:
        case QuickSetupActionMode.SAVE:
            _save(all_stages_form_data)
        case QuickSetupActionMode.EDIT:
            assert object_id is not None
            _edit(all_stages_form_data, object_id)
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
            assert object_id is not None
            _edit(all_stages_form_data, object_id)
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


def _edit(all_stages_form_data: ParsedFormData, object_id: str) -> None:
    config_file = NotificationRuleConfigFile()
    notification_rules = list(config_file.load_for_modification())
    for n, rule in enumerate(notification_rules):
        if rule["rule_id"] == object_id:
            notification_rules[n] = migrate_to_event_rule(
                cast(NotificationQuickSetupSpec, all_stages_form_data)
            )
            break
    config_file.save(notification_rules)


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
            id=ActionId("apply_and_test"),
            label=_("Apply & test notification rule"),
            action=save_and_test_action,
        ),
        QuickSetupAction(
            id=ActionId("apply_and_create_new"),
            label=_("Apply & create another rule"),
            action=save_and_new_action,
        ),
    ],
    load_data=load_notifications,
)
