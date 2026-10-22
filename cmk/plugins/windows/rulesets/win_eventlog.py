#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ipaddress
from collections.abc import Callable, Mapping

from cmk.rulesets.v1 import Help, Label, Message, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    List,
    MatchingScope,
    RegularExpression,
    SingleChoice,
    SingleChoiceElement,
    String,
    validators,
)
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic

_FILTER_KEYS = ("filter_ids", "filter_sources", "filter_users")


def _migrate_log(value: object) -> tuple[str, str | None]:
    match value:
        case "*":
            return "all", None
        case str() as name:
            return "named", name
        case _:
            raise ValueError(f"Unexpected value: {value!r}")


def _migrate_names(value: object) -> list[str]:
    match value:
        case "":
            # The old rule set stored an empty string for "include all" or "exclude none".
            return []
        case list() as names:
            return names
        case _:
            raise ValueError(f"Unexpected value: {value!r}")


def _migrate_event_log(value: object) -> Mapping[str, object]:
    match value:
        case (log, str() as severity, bool() as context):
            return {"log": _migrate_log(log), "severity": severity, "context": context}
        case _:
            raise ValueError(f"Unexpected value: {value!r}")


def _migrate_filter(value: object) -> Mapping[str, object]:
    match value:
        case (log, include, exclude):
            return {
                "log": _migrate_log(log),
                "include": _migrate_names(include),
                "exclude": _migrate_names(exclude),
            }
        case _:
            raise ValueError(f"Unexpected value: {value!r}")


def _migrate_text_pattern(value: object) -> Mapping[str, object]:
    match value:
        case (log, str() as pattern):
            return {"log": _migrate_log(log), "pattern": pattern}
        case _:
            raise ValueError(f"Unexpected value: {value!r}")


def _migrate_list(
    value: Mapping[str, object], key: str, migrate_item: Callable[[object], object]
) -> list[object]:
    match value.get(key, []):
        case list() as items:
            return [migrate_item(i) for i in items]
        case other:
            raise ValueError(f"Unexpected value: {other!r}")


def migrate(value: object) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"Unexpected value: {value!r}")
    if "logfiles" not in value:
        return value
    # Old rule ("first matching rule wins"): make all parameters explicit so that merging with
    # other rules does not change the outcome. The bakelet skips the empty lists, and the agent
    # does not use the Vista API by default.
    return {
        "event_logs": _migrate_list(value, "logfiles", _migrate_event_log),
        **{key: _migrate_list(value, key, _migrate_filter) for key in _FILTER_KEYS},
        "text_pattern": _migrate_list(value, "text_pattern", _migrate_text_pattern),
        "sendall": value.get("sendall", False),
        "skip_duplicated": value.get("skip_duplicated", False),
        "cluster_mapping": value.get("cluster_mapping", []),
        "vista_api": value.get("vista_api", False),
    }


def _log() -> CascadingSingleChoice:
    return CascadingSingleChoice(
        title=Title("Event log"),
        elements=(
            CascadingSingleChoiceElement(
                name="all",
                title=Title("All event logs"),
                parameter_form=FixedValue(value=None),
            ),
            CascadingSingleChoiceElement(
                name="named",
                title=Title("Specific event log"),
                parameter_form=String(custom_validate=(validators.LengthInRange(min_value=1),)),
            ),
        ),
        prefill=DefaultValue("all"),
    )


def _logfiles_element() -> List[Mapping[str, object]]:
    return List(
        title=Title("Configuration of individual event logs"),
        add_element_label=Label("Add tuning configuration"),
        element_template=Dictionary(
            elements={
                "log": DictElement(required=True, parameter_form=_log()),
                "severity": DictElement(
                    required=True,
                    parameter_form=SingleChoice(
                        title=Title("Severity"),
                        elements=[
                            SingleChoiceElement(name="warn", title=Title("WARN/CRIT")),
                            SingleChoiceElement(name="crit", title=Title("CRIT")),
                            SingleChoiceElement(name="all", title=Title("ALL")),
                            SingleChoiceElement(name="off", title=Title("disable")),
                        ],
                        prefill=DefaultValue("warn"),
                    ),
                ),
                "context": DictElement(
                    required=True,
                    parameter_form=BooleanChoice(
                        label=Label("with context"),
                        prefill=DefaultValue(True),
                    ),
                ),
            },
        ),
        help_text=Help(
            "Here, you can configure which messages should be discovered and "
            "reported from which event log. When you set the severity to <i>disabled</i> "
            "then this event log will totally be ignored. Unchecking <i>with context</i> "
            "will disable sending so-called context messages. When at least one new relevant "
            "message is being found in an event log, the agent usually sends <i>all</i> "
            "new messages from that check cycle. This makes it more convenient when viewing "
            "the messages in Checkmk. In high-volume log files it might be necessary "
            "to switch the context off in order to save networking and disk resources. "
            "<b>Note</b>: When several configuration tuning entries match for a log file "
            "then only the first one is being executed. So it does not make sense to "
            "create more then one entry for <i>All event logs</i>."
        ),
    )


def _sendall_element() -> BooleanChoice:
    return BooleanChoice(
        title=Title("Historic messages"),
        label=Label("Always send <b>all</b> messages, even old ones (just for testing!)"),
        help_text=Help(
            "This is just for testing! The agent will then always send "
            "all historic messages, not just the new ones. This leads "
            "to enormous amounts of data."
        ),
    )


def _skip_duplicated_element() -> BooleanChoice:
    return BooleanChoice(
        title=Title("Duplicated messages management"),
        label=Label("Filter out duplicated messages in Windows event log"),
        help_text=Help(
            "If Windows event log generates multiple messages with "
            "same content, then the agent delivers only the first message "
            "in the raw and the information how many times the message "
            "had been repeated: [this message had been repeated n times]. "
            "Setting this flag may help to decrease the size of the "
            "log in the case when too many same events have been generated."
        ),
    )


def _vista_api_element() -> BooleanChoice:
    return BooleanChoice(
        title=Title("Vista API"),
        label=Label("Activate modern event log API introduced in Vista"),
        help_text=Help(
            "Activate modern event log API introduced in Vista. "
            "Pro: supports new logs introduced with Vista. "
            "Contra: only on Vista (Server 2008) and newer, "
            "less well tested, maybe slower. "
            "Note: setting this does not change the default set "
            "of monitored logs, see log name for that."
        ),
    )


def _filter_ids_element() -> List[Mapping[str, object]]:
    return List(
        title=Title("Filtering by event ID"),
        help_text=Help("Here, you can configure messages filtering parameters."),
        add_element_label=Label("Add event ID filter rule"),
        element_template=Dictionary(
            elements={
                "log": DictElement(required=True, parameter_form=_log()),
                "include": DictElement(required=True, parameter_form=_include_id_range()),
                "exclude": DictElement(required=True, parameter_form=_exclude_id_range()),
            },
        ),
    )


def _filter_sources_element() -> List[Mapping[str, object]]:
    return List(
        title=Title("Filtering by event source"),
        help_text=Help("Here, you can configure messages filtering parameters."),
        add_element_label=Label("Add event source filter rule"),
        element_template=Dictionary(
            elements={
                "log": DictElement(required=True, parameter_form=_log()),
                "include": DictElement(required=True, parameter_form=_include_source_list()),
                "exclude": DictElement(required=True, parameter_form=_exclude_source_list()),
            },
        ),
    )


def _filter_users_element() -> List[Mapping[str, object]]:
    return List(
        title=Title("Filtering by event user"),
        help_text=Help("Here, you can configure messages filtering parameters using event user."),
        add_element_label=Label("Add event user filter rule"),
        element_template=Dictionary(
            elements={
                "log": DictElement(required=True, parameter_form=_log()),
                "include": DictElement(required=True, parameter_form=_include_user_list()),
                "exclude": DictElement(required=True, parameter_form=_exclude_user_list()),
            },
        ),
    )


def _text_pattern_element() -> List[Mapping[str, object]]:
    return List(
        title=Title("Filtering by message pattern"),
        help_text=Help(
            "Here, you can configure messages filtering parameters using regular expressions. "
            "The rule is case insensitive."
        ),
        add_element_label=Label("Add message pattern filter rule"),
        element_template=Dictionary(
            elements={
                "log": DictElement(required=True, parameter_form=_log()),
                "pattern": DictElement(
                    required=True,
                    parameter_form=RegularExpression(
                        title=Title("Regular expression"),
                        help_text=Help("Regular expression used to filter messages."),
                        predefined_help_text=MatchingScope.FULL,
                        custom_validate=(
                            validators.LengthInRange(min_value=1),
                            _validate_regex,
                        ),
                    ),
                ),
            },
        ),
    )


def _cluster_mapping_element() -> List[Mapping[str, object]]:
    return List(
        title=Title("Specify mappings of remote IPs to cluster names"),
        help_text=Help(
            "With this option activated cluster node IPs "
            "may be mapped to a cluster. In case the monitoring site "
            "is operated in a failover cluster configuration this option "
            "is required to prevent from potentially duplicated log entries."
        ),
        add_element_label=Label("Add cluster mapping"),
        element_template=Dictionary(
            elements={
                "name": DictElement(
                    required=True,
                    parameter_form=String(
                        title=Title("Name of the cluster"),
                        custom_validate=(
                            validators.MatchRegex(
                                r"^[A-Za-z_][-A-Za-z0-9_]*$",
                                error_msg=Message(
                                    "An identifier must only consist of letters, digits, dash "
                                    "and underscore and it must start with a letter or "
                                    "underscore."
                                ),
                            ),
                        ),
                    ),
                ),
                "ips": DictElement(
                    required=True,
                    parameter_form=List(
                        title=Title("Cluster node IPs"),
                        element_template=String(
                            title=Title("IPv4/IPv6 address"),
                            custom_validate=(_validate_ip_address,),
                        ),
                        custom_validate=(validators.LengthInRange(min_value=1),),
                    ),
                ),
            },
        ),
    )


def _validate_id(value: str) -> None:
    parts = value.replace(" ", "").split("-")
    try:
        if len(parts) > 2:
            raise ValueError(value)
        for part in parts:
            int(part)
    except ValueError as exception:
        raise validators.ValidationError(
            Message(
                "ID entry fields may contain either numeric event ID or pair of numeric event "
                "IDs separated by dash."
            )
        ) from exception


def _validate_text(value: str) -> None:
    if set(value) & {";", '"', "'", "*"}:
        raise validators.ValidationError(
            Message("The value must not contain any of the characters ; \" ' *")
        )


def _validate_regex(value: str) -> None:
    if "'" in value:
        raise validators.ValidationError(Message("The value must not contain the character '"))


def _validate_ip_address(value: str) -> None:
    try:
        ipaddress.ip_address(value)
    except ValueError as exception:
        raise validators.ValidationError(
            Message("Please enter a valid IPv4 or IPv6 address.")
        ) from exception


_ID_HELP = Help(
    "You may enter either a number, like 2345, or a range, like 20-2000. Leave the list empty to apply no restriction."
)
_ID_BUTTON = Label("Add event ID or event ID range")


def _include_id_range() -> List[str]:
    return List(
        title=Title("Include only messages with IDs"),
        help_text=_ID_HELP,
        add_element_label=_ID_BUTTON,
        element_template=String(
            custom_validate=(validators.LengthInRange(min_value=1), _validate_id),
        ),
    )


def _exclude_id_range() -> List[str]:
    return List(
        title=Title("Exclude messages with IDs"),
        help_text=_ID_HELP,
        add_element_label=_ID_BUTTON,
        element_template=String(
            custom_validate=(validators.LengthInRange(min_value=1), _validate_id),
        ),
    )


_SOURCE_HELP = Help("Enter source name. Leave the list empty to apply no restriction.")
_SOURCE_BUTTON = Label("Add source")


def _include_source_list() -> List[str]:
    return List(
        title=Title("Include messages only from sources"),
        help_text=_SOURCE_HELP,
        add_element_label=_SOURCE_BUTTON,
        element_template=String(
            custom_validate=(validators.LengthInRange(min_value=1), _validate_text),
        ),
    )


def _exclude_source_list() -> List[str]:
    return List(
        title=Title("Exclude messages from sources"),
        help_text=_SOURCE_HELP,
        add_element_label=_SOURCE_BUTTON,
        element_template=String(
            custom_validate=(validators.LengthInRange(min_value=1), _validate_text),
        ),
    )


_USER_HELP = Help("Enter username. Leave the list empty to apply no restriction.")
_USER_BUTTON = Label("Add user")


def _include_user_list() -> List[str]:
    return List(
        title=Title("Include messages only from users"),
        help_text=_USER_HELP,
        add_element_label=_USER_BUTTON,
        element_template=String(
            custom_validate=(validators.LengthInRange(min_value=1), _validate_text),
        ),
    )


def _exclude_user_list() -> List[str]:
    return List(
        title=Title("Exclude messages from users"),
        help_text=_USER_HELP,
        add_element_label=_USER_BUTTON,
        element_template=String(
            custom_validate=(validators.LengthInRange(min_value=1), _validate_text),
        ),
    )


def _valuespec_agent_config_win_eventlog() -> Dictionary:
    return Dictionary(
        migrate=migrate,
        elements={
            "event_logs": DictElement(parameter_form=_logfiles_element()),
            "filter_ids": DictElement(parameter_form=_filter_ids_element()),
            "filter_sources": DictElement(parameter_form=_filter_sources_element()),
            "filter_users": DictElement(parameter_form=_filter_users_element()),
            "text_pattern": DictElement(parameter_form=_text_pattern_element()),
            "sendall": DictElement(parameter_form=_sendall_element()),
            "skip_duplicated": DictElement(parameter_form=_skip_duplicated_element()),
            "cluster_mapping": DictElement(parameter_form=_cluster_mapping_element()),
            "vista_api": DictElement(parameter_form=_vista_api_element()),
        },
    )


rule_spec_win_eventlog = AgentConfig(
    title=Title("Fine-tune Windows event log monitoring"),
    name="win_eventlog",
    topic=Topic.WINDOWS,
    parameter_form=_valuespec_agent_config_win_eventlog,
)
