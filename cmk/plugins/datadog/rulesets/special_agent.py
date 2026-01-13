#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="exhaustive-match"

# mypy: disable-error-code="type-arg"

from collections.abc import Callable, Mapping

from cmk.ccc.version import Edition, edition
from cmk.gui.mkeventd import (
    service_levels,
    syslog_facilities,
    syslog_priorities,
)
from cmk.rulesets.internal.form_specs import ListExtended
from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    List,
    MatchingScope,
    migrate_to_password,
    migrate_to_proxy,
    Password,
    Proxy,
    RegularExpression,
    SingleChoice,
    SingleChoiceElement,
    String,
    TimeMagnitude,
    TimeSpan,
    validators,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic
from cmk.utils.paths import omd_root


def _valuespec_special_agents_datadog() -> Dictionary:
    return Dictionary(
        title=Title("Datadog"),
        help_text=Help("Configuration of the Datadog special agent."),
        elements={
            "instance": DictElement(
                required=True,
                parameter_form=Dictionary(
                    title=Title("Datadog instance"),
                    help_text=Help(
                        "Provide API host and credentials for your Datadog instance here."
                    ),
                    elements={
                        "api_key": DictElement(
                            required=True,
                            parameter_form=Password(
                                title=Title("API key"),
                                custom_validate=(validators.LengthInRange(min_value=1),),
                                migrate=migrate_to_password,
                            ),
                        ),
                        "app_key": DictElement(
                            required=True,
                            parameter_form=Password(
                                title=Title("Application Key"),
                                custom_validate=(validators.LengthInRange(min_value=1),),
                                migrate=migrate_to_password,
                            ),
                        ),
                        "api_host": DictElement(
                            required=True,
                            parameter_form=String(
                                title=Title("API host"),
                                prefill=DefaultValue("api.datadoghq.eu"),
                                custom_validate=(
                                    validators.Url(
                                        [validators.UrlProtocol.HTTP, validators.UrlProtocol.HTTPS]
                                    ),
                                ),
                            ),
                        ),
                    },
                ),
            ),
            "proxy": DictElement(
                required=False,
                parameter_form=Proxy(migrate=migrate_to_proxy),
            ),
            "monitors": DictElement(
                required=False,
                parameter_form=Dictionary(
                    title=Title("Fetch monitors"),
                    help_text=Help(
                        "Fetch monitors from your datadog instance. Fetched monitors will be "
                        "discovered as services on the host where the special agent is executed."
                    ),
                    elements={
                        "tags": DictElement(
                            required=False,
                            parameter_form=List(
                                title=Title("Restrict by tags"),
                                help_text=Help(
                                    "Restrict fetched monitors by tags (API field <tt>tags</tt>). "
                                    "Monitors must have all of the configured tags in order to be "
                                    "fetched."
                                ),
                                element_template=String(
                                    custom_validate=(validators.LengthInRange(min_value=1),)
                                ),
                                custom_validate=(validators.LengthInRange(min_value=1),),
                            ),
                        ),
                        "monitor_tags": DictElement(
                            required=False,
                            parameter_form=List(
                                title=Title("Restrict by monitor tags"),
                                help_text=Help(
                                    "Restrict fetched monitors by service and/or custom tags (API "
                                    "field <tt>monitor_tags</tt>). Monitors must have all of the "
                                    "configured tags in order to be fetched."
                                ),
                                element_template=String(
                                    custom_validate=(validators.LengthInRange(min_value=1),)
                                ),
                                custom_validate=(validators.LengthInRange(min_value=1),),
                            ),
                        ),
                    },
                ),
            ),
            **_fetch_events_and_logs_elements(),
        },
    )


def _fetch_events_and_logs_elements() -> Mapping[str, DictElement]:
    if edition(omd_root) is Edition.CLOUD:  # disabled in CSE
        return {}
    return {
        "events": DictElement(
            required=False,
            parameter_form=Dictionary(
                title=Title("Fetch events"),
                help_text=Help(
                    "Fetch events from the event stream of your datadog instance. Fetched "
                    "events will be forwared to the Event Console of the site where the "
                    "special agent is executed."
                ),
                elements={
                    "max_age": DictElement(
                        required=True,
                        parameter_form=TimeSpan(
                            title=Title("Maximum age of fetched events (10 hours max.)"),
                            help_text=Help(
                                "During each run, the agent will fetch events which are at "
                                "maximum this old. The agent memorizes events already fetched "
                                "during the last run, s.t. no event will be sent to the event "
                                "console multiple times. Setting this value lower than the "
                                "check interval of the host will result in missing events. "
                                "Also note that the Datadog API allows for creating new events "
                                "which lie in the past. Such events will be missed by the "
                                "agent if their age exceeds the value specified here."
                            ),
                            migrate=_migrate_to_float,
                            custom_validate=(
                                validators.NumberInRange(min_value=10, max_value=10 * 3600),
                            ),
                            prefill=DefaultValue(600),
                            displayed_magnitudes=[
                                TimeMagnitude.HOUR,
                                TimeMagnitude.MINUTE,
                                TimeMagnitude.SECOND,
                            ],
                        ),
                    ),
                    "tags": DictElement(
                        required=False,
                        parameter_form=List(
                            title=Title("Restrict by tags"),
                            help_text=Help(
                                "Restrict fetched events by tags (API field <tt>tags</tt>). "
                                "Events must have all of the configured tags in order to be "
                                "fetched."
                            ),
                            element_template=String(
                                custom_validate=(validators.LengthInRange(min_value=1),)
                            ),
                            custom_validate=(validators.LengthInRange(min_value=1),),
                        ),
                    ),
                    "tags_to_show": DictElement(
                        required=False,
                        parameter_form=List(
                            element_template=RegularExpression(
                                predefined_help_text=MatchingScope.PREFIX,
                            ),
                            title=Title("Tags shown in Event Console"),
                            help_text=Help(
                                "This option allows you to configure which Datadog tags will be "
                                "shown in the events forwarded to the Event Console. This is "
                                "done by entering regular expressions matching one or more "
                                "Datadog tags. Any matching tag will be added to the text of the "
                                "corresponding event."
                            ),
                            custom_validate=(validators.LengthInRange(min_value=1),),
                        ),
                    ),
                    "syslog_facility": DictElement(
                        required=True,
                        parameter_form=CascadingSingleChoice(
                            title=Title("Syslog facility"),
                            help_text=Help(
                                "Syslog facility of forwarded logs shown in Event Console."
                            ),
                            elements=[
                                CascadingSingleChoiceElement(
                                    name=name,
                                    title=Title(name),  # astrein: disable=localization-checker
                                    parameter_form=FixedValue(value=value, label=Label("")),
                                )
                                for value, name in syslog_facilities
                            ],
                            prefill=DefaultValue("user"),
                            migrate=_migrate_facility,
                        ),
                    ),
                    "syslog_priority": DictElement(
                        required=True,
                        parameter_form=CascadingSingleChoice(
                            title=Title("Syslog priority"),
                            help_text=Help(
                                "Syslog priority of forwarded events shown in Event Console."
                            ),
                            elements=[
                                CascadingSingleChoiceElement(
                                    name=name,
                                    title=Title(name),  # astrein: disable=localization-checker
                                    parameter_form=FixedValue(value=value, label=Label("")),
                                )
                                for value, name in syslog_priorities
                            ],
                            prefill=DefaultValue("alert"),
                            migrate=_migrate_priority,
                        ),
                    ),
                    "service_level": DictElement(
                        required=True,
                        parameter_form=CascadingSingleChoice(
                            elements=[
                                CascadingSingleChoiceElement(
                                    name=_format_service_level(value),
                                    title=Title(name),  # astrein: disable=localization-checker
                                    parameter_form=FixedValue(value=value, label=Label("")),
                                )
                                for value, name in service_levels()
                            ],
                            title=Title("Service level"),
                            help_text=Help(
                                "Service level of forwarded events shown in Event Console."
                            ),
                            migrate=_migrate_service_levels,
                        ),
                    ),
                    "add_text": DictElement(
                        required=True,
                        parameter_form=SingleChoice(
                            elements=[
                                SingleChoiceElement(
                                    name="do_not_add_text",
                                    title=Title("Do not add text"),
                                ),
                                SingleChoiceElement(
                                    name="add_text",
                                    title=Title("Add text"),
                                ),
                            ],
                            title=Title("Add text of events"),
                            prefill=DefaultValue("do_not_add_text"),
                            help_text=Help(
                                "Add text of events to data forwarded to the Event Console. "
                                "Newline characters are replaced by '~'."
                            ),
                            migrate=lambda value: value
                            if isinstance(value, str)
                            else "add_text"
                            if value is True
                            else "do_not_add_text",
                        ),
                    ),
                },
            ),
        ),
        "logs": DictElement(
            required=False,
            parameter_form=Dictionary(
                title=Title("Fetch logs"),
                help_text=Help(
                    "Fetch logs of your datadog instance. Fetched logs will be forwared to the "
                    "Event Console of the site where the special agent is executed."
                ),
                elements={
                    "max_age": DictElement(
                        required=True,
                        parameter_form=TimeSpan(
                            title=Title("Maximum age of fetched logs (10 hours max.)"),
                            help_text=Help(
                                "During each run, the agent will fetch logs which are at "
                                "maximum this old. The agent memorizes logs already fetched "
                                "during the last run, s.t. no logs will be sent to the event "
                                "console multiple times. Setting this value lower than the "
                                "check interval of the host will result in missing logs. "
                            ),
                            migrate=_migrate_to_float,
                            custom_validate=(
                                validators.NumberInRange(min_value=10, max_value=10 * 3600),
                            ),
                            prefill=DefaultValue(600),
                            displayed_magnitudes=[
                                TimeMagnitude.HOUR,
                                TimeMagnitude.MINUTE,
                                TimeMagnitude.SECOND,
                            ],
                        ),
                    ),
                    "query": DictElement(
                        required=True,
                        parameter_form=String(
                            title=Title("Log search query"),
                            help_text=Help(
                                "Query to speficy which logs should be forwarded to the event "
                                "console. Use the Datadog "
                                "<a href='https://docs.datadoghq.com/logs/explorer/search_syntax'>log search syntax</a>."
                            ),
                        ),
                    ),
                    "indexes": DictElement(
                        required=True,
                        parameter_form=ListExtended(
                            title=Title("Indexes to search"),
                            prefill=DefaultValue(["*"]),
                            help_text=Help(
                                "Indexes to search, defaults to '*', which means all indexes."
                            ),
                            element_template=String(),
                        ),
                    ),
                    "syslog_facility": DictElement(
                        required=True,
                        parameter_form=CascadingSingleChoice(
                            title=Title("Syslog facility"),
                            help_text=Help(
                                "Syslog facility of forwarded logs shown in Event Console."
                            ),
                            elements=[
                                CascadingSingleChoiceElement(
                                    name=name,
                                    title=Title(name),  # astrein: disable=localization-checker
                                    parameter_form=FixedValue(value=value, label=Label("")),
                                )
                                for value, name in syslog_facilities
                            ],
                            prefill=DefaultValue("user"),
                            migrate=_migrate_facility,
                        ),
                    ),
                    "service_level": DictElement(
                        required=True,
                        parameter_form=CascadingSingleChoice(
                            elements=[
                                CascadingSingleChoiceElement(
                                    name=_format_service_level(value),
                                    title=Title(name),  # astrein: disable=localization-checker
                                    parameter_form=FixedValue(value=value, label=Label("")),
                                )
                                for value, name in service_levels()
                            ],
                            title=Title("Service level"),
                            help_text=Help(
                                "Service level of forwarded events shown in Event Console."
                            ),
                            migrate=_migrate_service_levels,
                        ),
                    ),
                    "text": DictElement(
                        required=True,
                        parameter_form=ListExtended(
                            title=Title("Text of forwarded events"),
                            help_text=Help(
                                "The text of the event can be constructed from the "
                                "<a href='https://docs.datadoghq.com/api/latest/logs/#search-logs'>attributes section of a log entry</a>. "
                                "The text elements are rendered as 'Name:str(attributes[Key])', separated by a comma. "
                                "To access nested fields, use 'key.subkey'. Defaults to the message of the log."
                            ),
                            add_element_label=Label("new element"),
                            prefill=DefaultValue([{"name": "message", "key": "message"}]),
                            element_template=Dictionary(
                                elements={
                                    "name": DictElement(
                                        required=True, parameter_form=String(title=Title("Name"))
                                    ),
                                    "key": DictElement(
                                        required=True, parameter_form=String(title=Title("Key"))
                                    ),
                                },
                                migrate=_tuple_do_dict_with_keys("name", "key"),
                            ),
                        ),
                    ),
                },
            ),
        ),
    }


def _migrate_to_float(v: object) -> float:
    """
    >>> _migrate_to_float(1)
    1.0
    >>> _migrate_to_float(1.0)
    1.0
    """
    match v:
        case int() | float():
            return float(v)
    raise ValueError(f"Expected int or float, got {type(v)}")


def _tuple_do_dict_with_keys(*keys: str) -> Callable[[object], Mapping[str, object]]:
    def _tuple_to_dict(
        param: object,
    ) -> Mapping[str, object]:
        match param:
            case tuple():
                return dict(zip(keys, param))
            case dict() as already_migrated:
                return already_migrated
        raise ValueError(param)

    return _tuple_to_dict


def _migrate_facility(value: object) -> tuple[str, int]:
    match value:
        case tuple((str(s), int(i))):
            return (s, i)
        case int(i):
            return next((name, facility) for facility, name in syslog_facilities if facility == i)
    raise ValueError(f"Invalid facility value: {value!r}")


def _migrate_priority(value: object) -> tuple[str, int]:
    match value:
        case tuple((str(s), int(i))):
            return (s, i)
        case int(i):
            return next((name, priority) for priority, name in syslog_priorities if priority == i)
    raise ValueError(f"Invalid priority value: {value!r}")


def _migrate_service_levels(value: object) -> tuple[str, int]:
    match value:
        case tuple((str(s), int(i))) if s.startswith("internal_id_"):
            # Already migrated to e.g. ("internal_id_10", 10)
            return s, i
        case int(i) | tuple((str(_), int(i))):
            return next(
                (_format_service_level(i), value) for value, name in service_levels() if value == i
            )
    raise ValueError(f"Invalid priority value: {value!r}")


def _format_service_level(internal_id: int) -> str:
    return "internal_id_" + str(internal_id)


rule_spec_special_agent_datadog = SpecialAgent(
    name="datadog",
    title=Title("Datadog"),
    topic=Topic.APPLICATIONS,
    parameter_form=_valuespec_special_agents_datadog,
)
