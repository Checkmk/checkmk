#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import re
from collections.abc import Mapping, Sequence
from typing import assert_never, cast, Final, get_args, Literal

from livestatus import SiteConfiguration

import cmk.utils.paths
from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId
from cmk.ccc.version import Edition, edition
from cmk.gui.config import active_config
from cmk.gui.form_specs.unstable import (
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
    TwoColumnDictionary,
    World,
)
from cmk.gui.form_specs.unstable.cascading_single_choice_extended import (
    CascadingSingleChoiceElementExtended,
)
from cmk.gui.form_specs.unstable.legacy_converter import Tuple
from cmk.gui.form_specs.unstable.list_unique_selection import (
    UniqueCascadingSingleChoiceElement,
    UniqueSingleChoiceElement,
)
from cmk.gui.form_specs.unstable.multiple_choice import MultipleChoiceElementExtended
from cmk.gui.hooks import request_memoize
from cmk.gui.i18n import _
from cmk.gui.mkeventd import service_levels, syslog_facilities, syslog_priorities
from cmk.gui.quick_setup.private.widgets import (
    ConditionalNotificationDialogWidget,
    ConditionalNotificationECAlertStageWidget,
    ConditionalNotificationServiceEventStageWidget,
)
from cmk.gui.quick_setup.v0_unstable._registry import QuickSetupRegistry
from cmk.gui.quick_setup.v0_unstable.predefined import recaps
from cmk.gui.quick_setup.v0_unstable.setups import (
    ProgressLogger,
    QuickSetup,
    QuickSetupAction,
    QuickSetupActionButtonIcon,
    QuickSetupActionMode,
    QuickSetupStage,
    QuickSetupStageAction,
)
from cmk.gui.quick_setup.v0_unstable.type_defs import (
    ActionId,
    ParsedFormData,
    QuickSetupId,
    StageIndex,
)
from cmk.gui.quick_setup.v0_unstable.widgets import (
    Collapsible,
    Dialog,
    FormSpecId,
    FormSpecWrapper,
    Widget,
)
from cmk.gui.user_sites import get_activation_site_choices
from cmk.gui.userdb import load_users
from cmk.gui.wato._group_selection import sorted_contact_group_choices
from cmk.gui.wato.pages.notifications.migrate import (
    host_event_mapper,
    migrate_to_event_rule,
    migrate_to_notification_quick_setup_spec,
    service_event_mapper,
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
from cmk.gui.watolib.user_scripts import load_notification_scripts, NotificationUserScripts
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
    MonitoredHost,
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
    ListOfStringsLayout,
)
from cmk.utils.notify_types import HostEventType, ServiceEventType
from cmk.utils.tags import AuxTag, TagGroup
from cmk.utils.timeperiod import TimeperiodName

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


def _host_from_state_choices() -> Sequence[SingleChoiceElementExtended[int]]:
    return [SingleChoiceElementExtended(name=state, title=title) for state, title in _host_states()]


def _host_to_state_choices() -> Sequence[SingleChoiceElementExtended[int]]:
    return [
        SingleChoiceElementExtended(name=state, title=title)
        for state, title in _host_states()
        if state != -1
    ]


def _service_from_state_choices() -> Sequence[SingleChoiceElementExtended[int]]:
    return [
        SingleChoiceElementExtended(name=state, title=title) for state, title in _service_states()
    ]


def _service_to_state_choices() -> Sequence[SingleChoiceElementExtended[int]]:
    return [
        SingleChoiceElementExtended(name=state, title=title)
        for state, title in _service_states()
        if state != -1
    ]


def _validate_host_state_change(
    state_change: object,
) -> object:
    if not isinstance(state_change, tuple) or host_event_mapper(state_change) not in list(
        get_args(get_args(HostEventType)[0])
    ):
        raise ValidationError(Message("Invalid state change for host"))
    return state_change


def _validate_service_state_change(state_change: object) -> object:
    if not isinstance(state_change, tuple) or service_event_mapper(state_change) not in list(
        get_args(get_args(ServiceEventType)[0])
    ):
        raise ValidationError(Message("Invalid state change for service"))
    return state_change


def _event_choices(
    what: Literal["host", "service"],
) -> Sequence[UniqueCascadingSingleChoiceElement]:
    return [
        UniqueCascadingSingleChoiceElement(
            unique=False,
            parameter_form=CascadingSingleChoiceElementExtended(
                name="state_change",
                title=Title("State change"),
                parameter_form=Tuple(
                    layout="horizontal",
                    elements=[
                        SingleChoiceExtended(
                            label=Label("From"),
                            prefill=DefaultValue(-1),
                            elements=_host_from_state_choices()
                            if what == "host"
                            else _service_from_state_choices(),
                        ),
                        SingleChoiceExtended(
                            label=Label("to"),
                            prefill=DefaultValue(1) if what == "host" else DefaultValue(2),
                            elements=_host_to_state_choices()
                            if what == "host"
                            else _service_to_state_choices(),
                        ),
                    ],
                    custom_validate=[
                        _validate_host_state_change
                        if what == "host"
                        else _validate_service_state_change,
                    ],
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


def _validate_at_least_one_event(trigger_events: Mapping[str, object]) -> None:
    if not trigger_events:
        raise ValidationError(Message("At least one triggering event must be selected."))

    if "host_events" in trigger_events and not trigger_events["host_events"]:
        raise ValidationError(Message("At least one host event must be selected."))

    if "service_events" in trigger_events and not trigger_events["service_events"]:
        raise ValidationError(Message("At least one service event must be selected."))


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
                            parameter_form=TwoColumnDictionary(
                                default_checked=["host_events", "service_events"],
                                elements={
                                    "host_events": DictElement(
                                        parameter_form=ListUniqueSelection(
                                            title=Title("Host events"),
                                            help_text=Help(
                                                "Notifications are sent only for event types "
                                                "defined by the 'Notified events for "
                                                "hosts' ruleset. "
                                                "Note: Host events do not match "
                                                "this rule if a service filter "
                                                "matches. However, if an exclude "
                                                "service filter matches, host events are "
                                                "still matched by the rule."
                                            ),
                                            prefill=DefaultValue(
                                                [
                                                    ("state_change", (-1, HostState.DOWN)),
                                                    ("state_change", (-1, HostState.UP)),
                                                ]
                                            ),
                                            single_choice_type=CascadingSingleChoice,
                                            cascading_single_choice_layout=CascadingSingleChoiceLayout.horizontal,
                                            elements=_event_choices("host"),
                                            add_element_label=Label("Add event"),
                                        )
                                    ),
                                    "service_events": DictElement(
                                        parameter_form=ListUniqueSelection(
                                            title=Title("Service events"),
                                            help_text=Help(
                                                "Notifications are sent only for event types "
                                                "defined by the 'Notified events for "
                                                "services' ruleset"
                                            ),
                                            prefill=DefaultValue(
                                                [
                                                    ("state_change", (-1, ServiceState.CRIT)),
                                                    ("state_change", (-1, ServiceState.WARN)),
                                                    ("state_change", (-1, ServiceState.OK)),
                                                ]
                                            ),
                                            single_choice_type=CascadingSingleChoice,
                                            cascading_single_choice_layout=CascadingSingleChoiceLayout.horizontal,
                                            elements=_event_choices("service"),
                                            add_element_label=Label("Add event"),
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
                                custom_validate=[_validate_at_least_one_event],
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
                custom_validators=[],
                recap=[custom_recap_formspec_triggering_events],
                next_button_label=_("Next step: Specify host/services"),
            ),
        ],
    )


def custom_recap_formspec_triggering_events(
    quick_setup_id: QuickSetupId,
    stage_index: StageIndex,
    all_stages_form_data: ParsedFormData,
    progress_logger: ProgressLogger,
    site_configs: Mapping[SiteId, SiteConfiguration],
    debug: bool,
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
    return recaps.recaps_form_spec(
        quick_setup_id,
        stage_index,
        cleaned_stages_form_data,
        progress_logger,
        site_configs,
        debug=debug,
    )


def _get_contact_group_users() -> list[tuple[UserId, str]]:
    return sorted(
        (name, f"{name} - {user.get('alias', name)}")
        for name, user in load_users().items()
        if user.get("contactgroups")
    )


def _get_service_levels_single_choice() -> Sequence[SingleChoiceElementExtended[int]]:
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
                    conditions=[
                        Condition(name=tag_id, title=tag_title)
                        for tag_id, tag_title in tag.get_non_empty_tag_choices()
                    ],
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
    progress_logger: ProgressLogger,
    site_configs: Mapping[SiteId, SiteConfiguration],
    debug: bool,
) -> Sequence[Widget]:
    cleaned_stages_form_data = {
        form_spec_wrapper_id: form_data
        for form_spec_wrapper_id, form_data in all_stages_form_data.items()
        if len(form_data) > 0
    }
    return recaps.recaps_form_spec(
        quick_setup_id, stage_index, cleaned_stages_form_data, progress_logger, site_configs, debug
    )


class NonEmptyString:
    """Custom validator that ensures the string is not empty."""

    def __init__(self, error_msg: Message | None = None) -> None:
        self.error_msg: Final = error_msg or Message("Input cannot be empty")

    def __call__(self, value: str) -> None:
        if not value.strip():
            raise ValidationError(self.error_msg)


class IsValidRegularExpression:
    """Custom validator that checks if the string is a valid regular expression."""

    def __init__(self) -> None:
        self.error_msg: Final = Message(
            "Your input is not valid. You need to provide a regular expression (regex). For example"
            " you need to use \\\\ instead of \\ if you want to search for a"
            " single backslash."
        )

    def __call__(self, value: str) -> None:
        try:
            re.compile(value)
        except re.error:
            raise ValidationError(self.error_msg)


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
                                form_spec=TwoColumnDictionary(
                                    elements={
                                        "rule_ids": DictElement(
                                            parameter_form=ListExtended(
                                                title=Title("Rule IDs"),
                                                element_template=String(
                                                    field_size=FieldSize.MEDIUM,
                                                    custom_validate=[
                                                        NonEmptyString(
                                                            Message("Please add a Rule ID.")
                                                        )
                                                    ],
                                                ),
                                                editable_order=False,
                                                prefill=DefaultValue([]),
                                                custom_validate=[
                                                    not_empty(
                                                        error_msg=Message(
                                                            "Please add at least one Rule ID."
                                                        )
                                                    )
                                                ],
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
                                                custom_validate=[
                                                    NonEmptyString(
                                                        Message("Please add an event comment..")
                                                    )
                                                ],
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
                        form_spec=TwoColumnDictionary(
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
                                        custom_validate=[
                                            not_empty(
                                                error_msg=Message(
                                                    "Please add at least one host label."
                                                )
                                            )
                                        ],
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
                                        custom_validate=[
                                            not_empty(
                                                error_msg=Message(
                                                    "Please add at least one host group."
                                                )
                                            )
                                        ],
                                    ),
                                ),
                                "match_hosts": DictElement(
                                    parameter_form=ListOfStrings(
                                        title=Title("Hosts"),
                                        string_spec=MonitoredHost(),
                                        custom_validate=[
                                            not_empty(
                                                error_msg=Message("Please add at least one host.")
                                            )
                                        ],
                                    ),
                                ),
                                "exclude_hosts": DictElement(
                                    parameter_form=ListOfStrings(
                                        title=Title("Exclude hosts"),
                                        string_spec=MonitoredHost(),
                                        custom_validate=[
                                            not_empty(
                                                error_msg=Message("Please add at least one host.")
                                            ),
                                        ],
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
                            ConditionalNotificationDialogWidget(
                                items=[
                                    Dialog(
                                        text=_(
                                            "Note: Host events do not match "
                                            "this rule if a service filter "
                                            "matches. However, if an exclude "
                                            "filter matches, host events are "
                                            "still matched by the rule."
                                        ),
                                    )
                                ],
                                target="svc_filter",
                            ),
                            FormSpecWrapper(
                                id=FormSpecId("service_filters"),
                                form_spec=TwoColumnDictionary(
                                    elements={
                                        "service_labels": DictElement(
                                            parameter_form=Labels(
                                                title=Title("Service labels"),
                                                help_text=Help(
                                                    "Use this condition to select services based on the configured service labels."
                                                ),
                                                world=World.CORE,
                                                custom_validate=[
                                                    not_empty(
                                                        error_msg=Message(
                                                            "Please add at least one service label."
                                                        )
                                                    )
                                                ],
                                            ),
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
                                                custom_validate=[
                                                    not_empty(
                                                        error_msg=Message(
                                                            "Please add at least one service group."
                                                        )
                                                    )
                                                ],
                                            ),
                                        ),
                                        "match_service_groups_regex": DictElement(
                                            parameter_form=CascadingSingleChoiceExtended(
                                                prefill=DefaultValue("match_id"),
                                                layout=CascadingSingleChoiceLayout.button_group,
                                                help_text=Help(
                                                    "The text entered here is "
                                                    "handled as a regular "
                                                    "expression pattern. The "
                                                    "pattern is case-sensitive "
                                                    "and matches from the start. "
                                                    "Add '$' to match the whole "
                                                    "text."
                                                ),
                                                title=Title("Service groups (regex)"),
                                                elements=[
                                                    CascadingSingleChoiceElement(
                                                        name="match_id",
                                                        title=Title(
                                                            "Match the internal identifier"
                                                        ),
                                                        parameter_form=ListOfStrings(
                                                            string_spec=String(
                                                                field_size=FieldSize.MEDIUM,
                                                                custom_validate=[
                                                                    IsValidRegularExpression()
                                                                ],
                                                            ),
                                                        ),
                                                    ),
                                                    CascadingSingleChoiceElement(
                                                        name="match_alias",
                                                        title=Title("Match the alias"),
                                                        parameter_form=ListOfStrings(
                                                            string_spec=String(
                                                                field_size=FieldSize.MEDIUM,
                                                                custom_validate=[
                                                                    IsValidRegularExpression()
                                                                ],
                                                            ),
                                                        ),
                                                    ),
                                                ],
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
                                                custom_validate=[
                                                    not_empty(
                                                        error_msg=Message(
                                                            "Please add at least one service group."
                                                        )
                                                    )
                                                ],
                                            ),
                                        ),
                                        "exclude_service_groups_regex": DictElement(
                                            parameter_form=CascadingSingleChoiceExtended(
                                                prefill=DefaultValue("match_id"),
                                                layout=CascadingSingleChoiceLayout.button_group,
                                                help_text=Help(
                                                    "The text entered here is "
                                                    "handled as a regular "
                                                    "expression pattern. The "
                                                    "pattern is case-sensitive "
                                                    "and matches from the start. "
                                                    "Add '$' to match the whole "
                                                    "text."
                                                ),
                                                title=Title("Exclude service groups (regex)"),
                                                elements=[
                                                    CascadingSingleChoiceElement(
                                                        name="match_id",
                                                        title=Title("Internal identifier"),
                                                        parameter_form=ListOfStrings(
                                                            string_spec=String(
                                                                field_size=FieldSize.MEDIUM,
                                                                custom_validate=[
                                                                    IsValidRegularExpression()
                                                                ],
                                                            ),
                                                        ),
                                                    ),
                                                    CascadingSingleChoiceElement(
                                                        name="match_alias",
                                                        title=Title("Alias"),
                                                        parameter_form=ListOfStrings(
                                                            string_spec=String(
                                                                field_size=FieldSize.MEDIUM,
                                                                custom_validate=[
                                                                    IsValidRegularExpression()
                                                                ],
                                                            ),
                                                        ),
                                                    ),
                                                ],
                                            ),
                                        ),
                                        "match_services": DictElement(
                                            parameter_form=ListOfStrings(
                                                title=Title("Services"),
                                                help_text=Help(
                                                    "The text entered here is "
                                                    "handled as a regular "
                                                    "expression pattern. The "
                                                    "pattern is case-sensitive "
                                                    "and matches from the start. "
                                                    "Add '$' to match the whole "
                                                    "text."
                                                ),
                                                string_spec=String(
                                                    field_size=FieldSize.MEDIUM,
                                                    custom_validate=[IsValidRegularExpression()],
                                                ),
                                                custom_validate=[
                                                    not_empty(
                                                        error_msg=Message(
                                                            "Please add at least one service."
                                                        )
                                                    )
                                                ],
                                            ),
                                        ),
                                        "exclude_services": DictElement(
                                            parameter_form=ListOfStrings(
                                                title=Title("Exclude services"),
                                                help_text=Help(
                                                    "The text entered here is "
                                                    "handled as a regular "
                                                    "expression pattern. The "
                                                    "pattern is case-sensitive "
                                                    "and matches from the start. "
                                                    "Add '$' to match the whole "
                                                    "text."
                                                ),
                                                string_spec=String(
                                                    field_size=FieldSize.MEDIUM,
                                                    custom_validate=[IsValidRegularExpression()],
                                                ),
                                                custom_validate=[
                                                    not_empty(
                                                        error_msg=Message(
                                                            "Please add at least one service."
                                                        )
                                                    )
                                                ],
                                            ),
                                        ),
                                        "check_type_plugin": DictElement(
                                            parameter_form=MultipleChoiceExtended(
                                                title=Title("Check types"),
                                                help_text=Help(
                                                    "Only apply the rule if the "
                                                    "notification originates from "
                                                    "certain types of check plug-ins. "
                                                    "Note: Host notifications never "
                                                    "match this rule, if this option is "
                                                    "being used."
                                                ),
                                                elements=Autocompleter(
                                                    data=AutocompleterData(
                                                        ident="check_types",
                                                        params=AutocompleterParams(),
                                                    ),
                                                ),
                                                show_toggle_all=True,
                                                layout=MultipleChoiceExtendedLayout.dual_list,
                                                custom_validate=[
                                                    not_empty(
                                                        error_msg=Message(
                                                            "Please add at least one check type."
                                                        )
                                                    )
                                                ],
                                            ),
                                        ),
                                    },
                                ),
                            ),
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
                        form_spec=TwoColumnDictionary(
                            elements={
                                "contact_groups": DictElement(
                                    parameter_form=MultipleChoiceExtended(
                                        title=Title("Groups"),
                                        help_text=Help(
                                            "Filters hosts or services assigned "
                                            "to the selected contact groups. "
                                            "This filter only works with Checkmk "
                                            "Micro Core (CMC). If you are not "
                                            "using CMC, the filter will have no "
                                            "effect."
                                        ),
                                        elements=[
                                            MultipleChoiceElementExtended(
                                                name=name,
                                                title=Title("%s") % title,
                                            )
                                            for name, title in sorted_contact_group_choices()
                                        ],
                                        show_toggle_all=True,
                                        layout=MultipleChoiceExtendedLayout.dual_list,
                                        custom_validate=[
                                            not_empty(
                                                error_msg=Message(
                                                    "Please add at least one contact group."
                                                )
                                            )
                                        ],
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
                                        custom_validate=[
                                            not_empty(
                                                error_msg=Message("Please add at least one member.")
                                            )
                                        ],
                                    ),
                                ),
                            },
                        ),
                    ),
                ],
            ),
            Collapsible(
                title=_("General filters"),
                items=[
                    FormSpecWrapper(
                        id=FormSpecId("general_filters"),
                        form_spec=TwoColumnDictionary(
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
                                        title=Title("Folder (including subfolders)"),
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
                                            for name, title in get_activation_site_choices(
                                                active_config.sites
                                            )
                                        ],
                                        show_toggle_all=True,
                                        layout=MultipleChoiceExtendedLayout.dual_list,
                                        custom_validate=[
                                            not_empty(
                                                error_msg=Message("Please add at least one site.")
                                            )
                                        ],
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


def supports_bulk(script_name: str, notification_scripts: NotificationUserScripts) -> bool:
    if script_name not in notification_scripts:
        return False
    return notification_scripts[script_name].get("bulk", False)


def notification_method() -> QuickSetupStage:
    def bulk_notification_dict_element() -> DictElement[tuple[str, object]]:
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
        script_name: str,
        notification_scripts: NotificationUserScripts,
    ) -> dict[str, DictElement[tuple[str, object]]]:
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
                                    custom_validate=[
                                        not_empty(
                                            error_msg=Message("Please add at least one macro.")
                                        ),
                                    ],
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
        default_method_choice: DefaultValue[str] | InputHint[Title] = InputHint(
            Title("Please choose")
        )
        if script_choices := notification_script_choices():
            if "mail" in (name for name, title in script_choices):
                default_method_choice = DefaultValue("mail")
            else:
                default_method_choice = DefaultValue(script_choices[0][0])

        return [
            FormSpecWrapper(
                id=FormSpecId("notification_method"),
                form_spec=TwoColumnDictionary(
                    elements={
                        "notification_effect": DictElement(
                            required=True,
                            parameter_form=CascadingSingleChoiceExtended(
                                prefill=DefaultValue("send"),
                                layout=CascadingSingleChoiceLayout.button_group,
                                title=Title("Notification effect"),
                                help_text=Help(
                                    "Toggle to either send notifications or suppress all previous notifications for the method selected."
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
                                                for script_name, title in script_choices
                                            ],
                                            layout=CascadingSingleChoiceLayout.vertical,
                                            prefill=default_method_choice,
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
                                                for script_name, title in script_choices
                                            ],
                                            prefill=default_method_choice,
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


def _get_sorted_users() -> list[tuple[UserId, str]]:
    return sorted(
        (name, f"{name} - {user.get('alias', name)}") for name, user in load_users().items()
    )


def _contact_group_choice() -> Sequence[UniqueSingleChoiceElement]:
    return [
        UniqueSingleChoiceElement(
            parameter_form=SingleChoiceElementExtended(
                name=ident,
                title=Title(title),  # astrein: disable=localization-checker
            ),
        )
        for ident, title in sorted_contact_group_choices()
    ]


def custom_macros_cannot_be_empty(custom_macros: Sequence[tuple[str, str]]) -> None:
    for name, match in custom_macros:
        if not name.strip() and not match.strip():
            raise ValidationError(Message("A macro name and a regular expression are required"))
        if not name.strip():
            raise ValidationError(Message("A macro name is required"))
        if not match.strip():
            raise ValidationError(Message("A regular expression is required"))


def recipient() -> QuickSetupStage:
    def _components() -> Sequence[Widget]:
        recipient_elements = [
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
                        single_choice_prefill=InputHint(Title("Select contact group")),
                        single_choice_type=SingleChoice,
                        elements=_contact_group_choice(),
                        custom_validate=[
                            LengthInRange(
                                min_value=1,
                                error_msg=Message("Please add at least one contact group"),
                            )
                        ],
                    ),
                ),
            ),
        ]

        if edition(cmk.utils.paths.omd_root) != Edition.CLOUD:
            recipient_elements.append(
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
                                    error_msg=Message("Please add at least one email address"),
                                ),
                            ],
                        ),
                    ),
                )
            )

        recipient_elements.extend(
            [
                UniqueCascadingSingleChoiceElement(
                    parameter_form=CascadingSingleChoiceElementExtended(
                        title=Title("Specific users"),
                        name="specific_users",
                        parameter_form=ListUniqueSelection(
                            prefill=DefaultValue([]),
                            single_choice_prefill=InputHint(Title("Select user")),
                            single_choice_type=SingleChoice,
                            elements=[
                                UniqueSingleChoiceElement(
                                    parameter_form=SingleChoiceElementExtended(
                                        name=ident,
                                        title=Title(title),  # astrein: disable=localization-checker
                                    )
                                )
                                for ident, title in _get_sorted_users()
                            ],
                            custom_validate=[
                                LengthInRange(
                                    min_value=1,
                                    error_msg=Message("Please add at least one user"),
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
            ]
        )

        return [
            ConditionalNotificationDialogWidget(
                items=[
                    Dialog(
                        text=_(
                            "Select one user from a contact group with access "
                            "to all hosts and services. This will prevent "
                            "duplicate notifications, as selecting multiple "
                            "users will trigger separate notifications."
                        ),
                    )
                ],
                target="recipient",
            ),
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
                                elements=recipient_elements,
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
                                                help_text=Help(
                                                    "Restricts the list of "
                                                    "contacts created by the "
                                                    "previous options to those "
                                                    "who are members of the "
                                                    "selected contact groups. If "
                                                    "more than one contact group "
                                                    "is selected, the contact "
                                                    "must be a member of all "
                                                    "selected groups."
                                                ),
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
                                                            custom_validate=[
                                                                not_empty(
                                                                    error_msg=Message(
                                                                        "Please enter a name."
                                                                    )
                                                                )
                                                            ],
                                                        ),
                                                        String(
                                                            title=Title(
                                                                "Required match (regular expression)"
                                                            ),
                                                            custom_validate=[
                                                                not_empty(
                                                                    error_msg=Message(
                                                                        "Please enter a required match."
                                                                    )
                                                                )
                                                            ],
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
                                                    custom_macros_cannot_be_empty,
                                                ],
                                            ),
                                        ),
                                    ),
                                ],
                            ),
                        ),
                    }
                ),
            ),
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
    return sorted((name, f"{name} - {spec['alias']}") for name, spec in load_timeperiods().items())


def validate_notification_count_values(values: tuple[object, ...]) -> None:
    match values:
        case (int(lower_bound), _) if lower_bound < 1:
            raise ValidationError(Message("The lower bound must be greater than 0."))
        case (_, int(upper_bound)) if upper_bound < 1:
            raise ValidationError(Message("The upper bound must be greater than 0."))
        case (int(lower_bound), int(upper_bound)) if lower_bound > upper_bound:
            raise ValidationError(Message("The lower bound is greater than the upper bound."))
        case (int(_), int(_)):
            return
        case _:
            raise ValidationError(Message("Unexpected 'notification count' values passed to form."))


def validate_throttling_values(values: tuple[object, ...]) -> None:
    match values:
        case (int(notification_number), _) if notification_number < 1:
            raise ValidationError(
                Message("The 'notification number' value must be greater than 0.")
            )
        case (_, int(every_n_notification)) if every_n_notification < 1:
            raise ValidationError(Message("The 'send every' value must be greater than 0."))
        case (int(_), int(_)):
            return
        case _:
            raise ValidationError(Message("Unexpected 'throttling' values passed to form."))


def sending_conditions() -> QuickSetupStage:
    def _components() -> Sequence[Widget]:
        return [
            FormSpecWrapper(
                id=FormSpecId("sending_conditions"),
                form_spec=DictionaryExtended(
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
                                                    title=Title(  # astrein: disable=localization-checker
                                                        title
                                                    ),
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
                                            custom_validate=[validate_notification_count_values],
                                        )
                                    ),
                                    "throttle_periodic": DictElement(
                                        parameter_form=Tuple(
                                            title=Title("Throttling of 'Periodic notifications'"),
                                            help_text=Help(
                                                "Only applies to problem notifications and if periodic notifications are enabled."
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
                                            custom_validate=[validate_throttling_values],
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
                                            help_text=Help(
                                                "The text entered here is "
                                                "handled as a regular expression "
                                                "pattern. The pattern is "
                                                "case-sensitive and matches from "
                                                "the start. Add '$' to match the "
                                                "whole text."
                                            ),
                                            custom_validate=[
                                                not_empty(
                                                    error_msg=Message(
                                                        "Enter a plugin output to define what to filter for."
                                                    )
                                                ),
                                                IsValidRegularExpression(),
                                            ],
                                        )
                                    ),
                                    "custom_by_comment": DictElement(
                                        parameter_form=String(
                                            title=Title("'Custom notifications' by comment"),
                                            help_text=Help(
                                                "The text entered here is "
                                                "handled as a regular expression "
                                                "pattern. The pattern is "
                                                "case-sensitive and matches from "
                                                "the start. Add '$' to match the "
                                                "whole text."
                                            ),
                                            custom_validate=[
                                                not_empty(
                                                    error_msg=Message(
                                                        "Please enter a comment to filter for."
                                                    )
                                                ),
                                                IsValidRegularExpression(),
                                            ],
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
                form_spec=TwoColumnDictionary(
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
    all_stages_form_data: ParsedFormData,
    mode: QuickSetupActionMode,
    _progress_logger: ProgressLogger,
    object_id: str | None,
    use_git: bool,
    pprint_value: bool,
) -> str:
    match mode:
        case QuickSetupActionMode.SAVE:
            _save(all_stages_form_data, use_git=use_git, pprint_value=pprint_value)
            result_msg = _("New notification rule successfully created!")
        case QuickSetupActionMode.EDIT:
            assert object_id is not None
            _edit(all_stages_form_data, object_id, use_git=use_git, pprint_value=pprint_value)
            result_msg = _("Notification rule successfully edited!")
        case _:
            raise ValueError(f"Unknown mode {mode}")
    return mode_url("test_notifications", result=result_msg)


def save_and_new_action(
    all_stages_form_data: ParsedFormData,
    mode: QuickSetupActionMode,
    _progress_logger: ProgressLogger,
    object_id: str | None,
    use_git: bool,
    pprint_value: bool,
) -> str:
    match mode:
        case QuickSetupActionMode.SAVE:
            _save(all_stages_form_data, use_git=use_git, pprint_value=pprint_value)
            result_msg = _("New notification rule successfully created!")
        case QuickSetupActionMode.EDIT:
            assert object_id is not None
            _edit(all_stages_form_data, object_id, use_git=use_git, pprint_value=pprint_value)
            result_msg = _("Notification rule successfully edited!")
        case _:
            raise ValueError(f"Unknown mode {mode}")
    return mode_url(
        "notification_rule_quick_setup",
        result=result_msg,
    )


def register(quick_setup_registry: QuickSetupRegistry) -> None:
    quick_setup_registry.register(quick_setup_notifications)


def _save(all_stages_form_data: ParsedFormData, *, use_git: bool, pprint_value: bool) -> None:
    config_file = NotificationRuleConfigFile()
    notifications_rules = list(config_file.load_for_modification())
    notifications_rules += [
        migrate_to_event_rule(cast(NotificationQuickSetupSpec, all_stages_form_data))
    ]
    config_file.rule_created(
        notifications_rules,
        pprint_value=pprint_value,
        use_git=use_git,
    )


def _edit(
    all_stages_form_data: ParsedFormData, object_id: str, *, use_git: bool, pprint_value: bool
) -> None:
    config_file = NotificationRuleConfigFile()
    notification_rules = list(config_file.load_for_modification())
    rule_nr = "N/A"
    for n, rule in enumerate(notification_rules):
        if rule["rule_id"] == object_id:
            notification_rules[n] = migrate_to_event_rule(
                cast(NotificationQuickSetupSpec, all_stages_form_data)
            )
            rule_nr = str(n)
            break

    config_file.rule_updated(
        rules=notification_rules, rule_number=rule_nr, pprint_value=pprint_value, use_git=use_git
    )


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
            icon=QuickSetupActionButtonIcon(name="checkmark-plus"),
            action=save_and_new_action,
        ),
    ],
    load_data=load_notifications,
)
