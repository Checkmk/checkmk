#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re

from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsAgentPlugins
from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import (
    Checkbox,
    Dictionary,
    DropdownChoice,
    HostAddress,
    ID,
    ListOf,
    ListOfStrings,
    OptionalDropdownChoice,
    RegExp,
    TextInput,
    Tuple,
)
from cmk.utils.rulesets.definition import RuleGroup

error_message = _(
    "ID entry fields may contain either numeric event ID or pair of numeric event IDs "
    "separated by dash."
)


def _logfiles_element() -> tuple[str, ListOf[tuple[str, list[str], list[str]]]]:
    return (
        "logfiles",
        ListOf(
            valuespec=Tuple(
                elements=[
                    OptionalDropdownChoice(
                        choices=[("*", _("All event logs"))],
                        otherlabel=_("Event log:"),
                        explicit=TextInput(
                            allow_empty=False,
                            size=20,
                        ),
                    ),
                    DropdownChoice(
                        choices=[
                            ("warn", _("WARN/CRIT")),
                            ("crit", _("CRIT")),
                            ("all", _("ALL")),
                            ("off", _("disable")),
                        ],
                        default_value="warn",
                    ),
                    DropdownChoice(
                        choices=[
                            (True, _("with context")),
                            (False, _("without context")),
                        ]
                    ),
                ],
                orientation="horizontal",
            ),
            movable=True,
            title=_("Configuration of individual event logs"),
            help=_(
                "Here you can configure which messages should be discovered and "
                "reported from which Eventlog. When you set the severity to <i>disabled</i> "
                "then this Eventlog will totally be ignored. The switch <i>without context</i> "
                "will disable sending so-called context messages. When at least one new relevant "
                "message is being found in an Eventlog, the agent usually sends <i>all</i> "
                "new messages from that check cycle. This makes it more convenient when viewing "
                "the messages in Checkmk. In high-volume logfiles it might be necessary "
                "to switch the context off in order to save networking and disk resources. "
                "<b>Note</b>: When several configuration tuning entries match for a logfile "
                "then only the first one is being executed. So it does not make sense to "
                "create more then one entry for <i>All Eventlogs</i>."
            ),
            add_label=_("Add tuning configuration"),
        ),
    )


def _sendall_element() -> tuple[str, Checkbox]:
    return (
        "sendall",
        Checkbox(
            title=_("Historic messages"),
            label=_("Always send <b>all</b> messages, even old ones (just for testing!)"),
            help=_(
                "This is just for testing! The agent will then always send "
                "all historic messages, not just the new ones. This leads "
                "to enormous amounts of data."
            ),
        ),
    )


def _skip_duplicated_element() -> tuple[str, Checkbox]:
    return (
        "skip_duplicated",
        Checkbox(
            title=_("Duplicated messages management"),
            label=_("Filter out duplicated messages in Windows event log"),
            help=_(
                "If Windows event log generates multiple messages with "
                "same content, then the agent delivers only the first message "
                "in the raw and the information how many times the message "
                "had been repeated: [this message had been repeated n times]. "
                "Setting this flag may help to decrease the size of the "
                "log in the case when too many same events have been generated."
            ),
        ),
    )


def _vista_api_element() -> tuple[str, Checkbox]:
    return (
        "vista_api",
        Checkbox(
            title=_("Vista API"),
            label=_("Activate modern event log API introduced in Vista"),
            help=_(
                "Activate modern event log API introduced in Vista. "
                "Pro: supports new logs introduced with Vista. "
                "Contra: only on Vista (Server 2008) and newer, "
                "less well tested, maybe slower. "
                "Note: setting this does not change the default set o"
                "f monitored logs, see log name for that."
            ),
        ),
    )


def _filter_ids_element() -> tuple[str, ListOf[tuple[str, list[str], list[str]]]]:
    return (
        "filter_ids",
        ListOf(
            valuespec=Tuple(
                elements=[
                    OptionalDropdownChoice(
                        choices=[("*", _("All event logs"))],
                        otherlabel=_("Event log:"),
                        default_value="*",
                        explicit=TextInput(
                            allow_empty=False,
                            size=20,
                        ),
                    ),
                    _include_id_range(),
                    _exclude_id_range(),
                ],
                orientation="horizontal",
            ),
            title=_("Filtering by event ID"),
            movable=True,
            help=_("Here you can configure messages filtering parameters"),
            add_label=_("Add event ID filter rule"),
        ),
    )


def _filter_sources_element() -> tuple[str, ListOf[tuple[str, list[str], list[str]]]]:
    return (
        "filter_sources",
        ListOf(
            valuespec=Tuple(
                elements=[
                    OptionalDropdownChoice(
                        choices=[("*", _("All event logs"))],
                        otherlabel=_("Event log:"),
                        default_value="*",
                        explicit=TextInput(
                            allow_empty=False,
                            size=20,
                        ),
                    ),
                    _include_source_list(),
                    _exclude_source_list(),
                ],
                orientation="horizontal",
            ),
            movable=True,
            title=_("Filtering by event source"),
            help=_("Here you can configure messages filtering parameters"),
            add_label=_("Add event source filter rule"),
        ),
    )


def _filter_users_element() -> tuple[str, ListOf[tuple[str, list[str], list[str]]]]:
    return (
        "filter_users",
        ListOf(
            valuespec=Tuple(
                elements=[
                    OptionalDropdownChoice(
                        choices=[("*", _("All event logs"))],
                        otherlabel=_("Event log:"),
                        default_value="*",
                        explicit=TextInput(
                            allow_empty=False,
                            size=20,
                        ),
                    ),
                    _include_user_list(),
                    _exclude_user_list(),
                ],
                orientation="horizontal",
            ),
            movable=True,
            title=_("Filtering by event user"),
            help=_("Here you can configure messages filtering parameters using event user"),
            add_label=_("Add event user filter rule"),
        ),
    )


def _text_pattern_element() -> tuple[str, ListOf[tuple[str, str]]]:
    return (
        "text_pattern",
        ListOf(
            valuespec=Tuple(
                elements=[
                    OptionalDropdownChoice(
                        choices=[("*", _("All event logs"))],
                        otherlabel=_("Event log:"),
                        default_value="*",
                        explicit=TextInput(
                            allow_empty=False,
                            size=20,
                        ),
                    ),
                    RegExp(
                        title=_("Regular expression"),
                        mode="complete",
                        help=_("Regular expression used to filter messages."),
                        allow_empty=False,
                        size=80,
                        forbidden_chars="'",
                    ),
                ],
                orientation="horizontal",
            ),
            movable=True,
            title=_("Filtering by message pattern"),
            help=_(
                "Here you can configure messages filtering parameters using regular expressions. The rule is case insensitive."
            ),
            add_label=_("Add message pattern filter rule"),
        ),
    )


def _cluster_mapping_element() -> tuple[str, ListOf[dict[str, object]]]:
    return (
        "cluster_mapping",
        ListOf(
            valuespec=Dictionary(
                elements=[
                    (
                        "name",
                        ID(
                            title=_("Name of the cluster"),
                            size=40,
                            allow_empty=False,
                        ),
                    ),
                    (
                        "ips",
                        ListOfStrings(
                            title=_("Cluster node IPs"),
                            valuespec=HostAddress(
                                title=_("IPv4/IPv6 address"),
                                allow_host_name=False,
                                allow_empty=False,
                            ),
                            orientation="horizontal",
                            allow_empty=False,
                        ),
                    ),
                ],
                optional_keys=False,
            ),
            title=_("Specify mappings of remote IPs to cluster names"),
            help=_(
                "With this option activated cluster node IPs "
                "may be mapped to a cluster. In case the monitoring site "
                "is operated in a failover cluster configuration this option "
                "is required to prevent from potentially duplicated log entries."
            ),
            add_label=_("Add cluster mapping"),
        ),
    )


def _validate_id(text: str | None, var_prefix: str) -> None:
    # MonitoredHostname accepts also Nones
    if text is None:
        return

    text = text.replace(" ", "")

    if "-" in text:
        a, b, *c = text.split("-")
        if len(c) > 0:
            raise MKUserError(
                var_prefix,
                error_message + ":" + text,
            )
        try:
            __ = int(a)
        except ValueError as exception:
            raise MKUserError(
                var_prefix,
                error_message + ":" + text + " " + a,
            ) from exception
        try:
            __ = int(b)
        except ValueError as exception:
            raise MKUserError(
                var_prefix,
                error_message + ":" + text + " " + b,
            ) from exception

        return

    try:
        __ = int(text)
    except ValueError as exception:
        raise MKUserError("varprefix", error_message) from exception


def _validate_text(text: str | None, var_prefix: str) -> None:
    # MonitoredHostname accepts also Nones
    if text is None:
        return

    if set(text) & {";", '"', "'", "*"}:
        raise MKUserError(var_prefix, "{text} contains forbidden symbols")


def _validate_regex(text: str | None, var_prefix: str) -> None:
    # MonitoredHostname accepts also Nones
    if text is None:
        return

    try:
        re.compile(text)
    except re.error as exception:
        raise MKUserError(var_prefix, "{text} is not a valid regex") from exception

    if set(text) & {"'"}:
        raise MKUserError(var_prefix, "{text} contains forbidden symbol '")


_ID_HELP = _("You may enter either a number, like 2345, or a range, like 20-2000")
_ID_BUTTON = _("Add event ID or event ID range")


def _include_id_range() -> OptionalDropdownChoice[list[str]]:
    return OptionalDropdownChoice(
        choices=[("", _("Include all messages"))],
        otherlabel=_("Include only messages with IDs:"),
        default_value=[],
        explicit=ListOf(
            valuespec=TextInput(
                allow_empty=False,
                validate=_validate_id,
            ),
            movable=True,
            help=_ID_HELP,
            add_label=_ID_BUTTON,
        ),
    )


def _exclude_id_range() -> OptionalDropdownChoice[list[str]]:
    return OptionalDropdownChoice(
        choices=[("", _("Do not exclude messages"))],
        otherlabel=_("Exclude messages with IDs:"),
        default_value=[],
        explicit=ListOf(
            valuespec=TextInput(
                allow_empty=False,
                validate=_validate_id,
            ),
            movable=True,
            help=_ID_HELP,
            add_label=_ID_BUTTON,
        ),
    )


_SOURCE_HELP = _("Enter source name")
_SOURCE_BUTTON = _("Add source")


def _include_source_list() -> OptionalDropdownChoice[list[str]]:
    return OptionalDropdownChoice(
        choices=[("", _("Include all"))],
        otherlabel=_("Include messages only from sources:"),
        default_value=[],
        explicit=ListOf(
            valuespec=TextInput(
                allow_empty=False,
                validate=_validate_text,
            ),
            movable=True,
            help=_SOURCE_HELP,
            add_label=_SOURCE_BUTTON,
        ),
    )


def _exclude_source_list() -> OptionalDropdownChoice[list[str]]:
    return OptionalDropdownChoice(
        choices=[("", _("Do not exclude"))],
        otherlabel=_("Exclude messages from sources:"),
        default_value=[],
        explicit=ListOf(
            valuespec=TextInput(
                allow_empty=False,
                validate=_validate_text,
            ),
            movable=True,
            help=_SOURCE_HELP,
            add_label=_SOURCE_BUTTON,
        ),
    )


_USER_HELP = _("Enter username")
_USER_BUTTON = _("Add user")


def _include_user_list() -> OptionalDropdownChoice[list[str]]:
    return OptionalDropdownChoice(
        choices=[("", _("Include all"))],
        otherlabel=_("Include messages only from users:"),
        default_value=[],
        explicit=ListOf(
            valuespec=TextInput(
                allow_empty=False,
                validate=_validate_text,
            ),
            movable=True,
            help=_USER_HELP,
            add_label=_USER_BUTTON,
        ),
    )


def _exclude_user_list() -> OptionalDropdownChoice[list[str]]:
    return OptionalDropdownChoice(
        choices=[("", _("Do not exclude"))],
        otherlabel=_("Exclude messages from users:"),
        default_value=[],
        explicit=ListOf(
            valuespec=TextInput(
                allow_empty=False,
                validate=_validate_text,
            ),
            movable=True,
            help=_USER_HELP,
            add_label=_USER_BUTTON,
        ),
    )


def _valuespec_agent_config_win_eventlog() -> Dictionary:
    return Dictionary(
        title=_("Fine-tune Windows event log monitoring"),
        elements=[
            _logfiles_element(),
            _filter_ids_element(),
            _filter_sources_element(),
            _filter_users_element(),
            _text_pattern_element(),
            _sendall_element(),
            _skip_duplicated_element(),
            _cluster_mapping_element(),
            _vista_api_element(),
        ],
        optional_keys=[
            "vista_api",
            "filter_ids",
            "filter_sources",
            "filter_users",
            "cluster_mapping",
            "text_pattern",
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsAgentPlugins,
        name=RuleGroup.AgentConfig("win_eventlog"),
        valuespec=_valuespec_agent_config_win_eventlog,
    )
)
