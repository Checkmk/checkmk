#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
from collections.abc import Callable, Sequence
from typing import Generic, Literal, TypeVar

from cmk.ccc.version import Edition, edition

from cmk.utils import paths
from cmk.utils.notify_types import EventRule

from cmk.gui.config import active_config
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.userdb import UserSelection
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.valuespec import (
    DictionaryEntry,
    DropdownChoice,
    DualListChoice,
    Labels,
    ListChoice,
    ListOf,
    ListOfStrings,
    RegExp,
    Tuple,
)
from cmk.gui.watolib.hosts_and_folders import folder_tree
from cmk.gui.watolib.mode import WatoMode
from cmk.gui.watolib.timeperiods import TimeperiodSelection

from .._check_plugin_selection import CheckPluginSelection
from .._group_selection import sorted_contact_group_choices, sorted_service_group_choices
from ._match_conditions import common_host_rule_match_conditions, site_rule_match_condition

_T_EventSpec = TypeVar("_T_EventSpec", bound=EventRule | dict)


class ABCEventsMode(WatoMode, abc.ABC, Generic[_T_EventSpec]):
    @classmethod
    @abc.abstractmethod
    def _rule_match_conditions(cls):
        raise NotImplementedError()

    @classmethod
    def _event_rule_match_conditions(
        cls,
        flavour: Literal["notify", "alerts"],
    ) -> list[tuple[str, ListChoice]]:
        if flavour == "notify":
            add_choices = [
                ("f", _("Start or end of flapping state")),
                ("s", _("Start or end of a scheduled downtime")),
                ("x", _("Acknowledgment of problem")),
                ("as", _("Alert handler execution, successful")),
                ("af", _("Alert handler execution, failed")),
            ]
            add_default = ["f", "s", "x", "as", "af"]
        else:
            add_choices = []
            add_default = []

        return [
            (
                "match_host_event",
                ListChoice(
                    title=_("Match host event type"),
                    help=(
                        _(
                            "Select the host event types and transitions this rule should handle.<br>"
                            "Note: If you activate this option and do <b>not</b> also specify service event "
                            "types then this rule will never hold for service notifications!<br>"
                            'Note: You can only match on event types <a href="%s">created by the core</a>.'
                        )
                        % "wato.py?mode=edit_ruleset&varname=extra_host_conf%3Anotification_options"
                    ),
                    choices=_get_host_event_choices(add_choices),
                    default_value=[
                        "rd",
                        "dr",
                    ]
                    + add_default,
                ),
            ),
            (
                "match_service_event",
                ListChoice(
                    title=_("Match service event type"),
                    help=(
                        _(
                            "Select the service event types and transitions this rule should handle.<br>"
                            "Note: If you activate this option and do <b>not</b> also specify host event "
                            "types then this rule will never hold for host notifications!<br>"
                            'Note: You can only match on event types <a href="%s">created by the core</a>.'
                        )
                        % "wato.py?mode=edit_ruleset&varname=extra_service_conf%3Anotification_options"
                    ),
                    choices=_get_service_event_choices(flavour, add_choices),
                    default_value=[
                        "rw",
                        "rc",
                        "ru",
                        "wc",
                        "wu",
                        "uc",
                    ]
                    + add_default,
                ),
            ),
        ]

    @classmethod
    def _generic_rule_match_conditions(cls) -> list[DictionaryEntry]:
        return _simple_host_rule_match_conditions() + [
            (
                "match_servicelabels",
                Labels(
                    world=Labels.World.CORE,
                    title=_("Match service labels"),
                    help=_(
                        "Use this condition to select hosts based on the configured service labels."
                    ),
                ),
            ),
            (
                "match_servicegroups",
                DualListChoice(
                    title=_("Match service groups"),
                    help=_(
                        "The service must be in one of the selected service groups. For host events this condition "
                        "never matches as soon as at least one group is selected."
                    ),
                    allow_empty=False,
                    choices=sorted_service_group_choices,
                ),
            ),
            (
                "match_exclude_servicegroups",
                DualListChoice(
                    title=_("Exclude service groups"),
                    help=_(
                        "The service must not be in one of the selected service groups. For host events this condition "
                        "is simply ignored."
                    ),
                    allow_empty=False,
                    choices=sorted_service_group_choices,
                ),
            ),
            (
                "match_servicegroups_regex",
                Tuple(
                    title=_("Match service groups (regex)"),
                    elements=[
                        DropdownChoice(
                            choices=[
                                ("match_id", _("Match the internal identifier")),
                                ("match_alias", _("Match the alias")),
                            ],
                            default_value="match_id",
                        ),
                        ListOfStrings(
                            help=_(
                                "The service group alias must match one of the following regular expressions."
                                " For host events this condition never matches as soon as at least one group is selected."
                            ),
                            valuespec=RegExp(
                                size=40,
                                mode=RegExp.infix,
                            ),
                            orientation="horizontal",
                        ),
                    ],
                ),
            ),
            (
                "match_exclude_servicegroups_regex",
                Tuple(
                    title=_("Exclude service groups (regex)"),
                    elements=[
                        DropdownChoice(
                            choices=[
                                ("match_id", _("Match the internal identifier")),
                                ("match_alias", _("Match the alias")),
                            ],
                            default_value="match_id",
                        ),
                        ListOfStrings(
                            help=_(
                                "The service group alias must not match one of the following regular expressions. "
                                "For host events this condition is simply ignored."
                            ),
                            valuespec=RegExp(
                                size=40,
                                mode=RegExp.infix,
                            ),
                            orientation="horizontal",
                        ),
                    ],
                ),
            ),
            (
                "match_services",
                ListOfStrings(
                    title=_("Match services"),
                    help=_(
                        "Specify a list of regular expressions that must match the <b>beginning</b> of the "
                        "service name in order for the rule to match. Note: Host notifications never match this "
                        "rule if this option is being used."
                    ),
                    valuespec=RegExp(
                        size=40,
                        mode=RegExp.prefix,
                    ),
                    orientation="horizontal",
                    allow_empty=False,
                    empty_text=_(
                        "Please specify at least one service regex. Disable the option if you want to allow all services."
                    ),
                ),
            ),
            (
                "match_exclude_services",
                ListOfStrings(
                    title=_("Exclude services"),
                    valuespec=RegExp(
                        size=40,
                        mode=RegExp.prefix,
                    ),
                    orientation="horizontal",
                ),
            ),
            (
                "match_checktype",
                CheckPluginSelection(
                    title=_("Match check types"),
                    help_=_(
                        "Only apply the rule if the notification originates from certain types of check plug-ins. "
                        "Note: Host notifications never match this rule, if this option is being used."
                    ),
                ),
            ),
            (
                "match_plugin_output",
                RegExp(
                    title=_("Match check plug-in output"),
                    help=_(
                        "This text is a regular expression that is being searched in the output "
                        "of the check plug-ins that produced the alert. It is not a prefix but an infix match."
                    ),
                    size=40,
                    mode=RegExp.prefix,
                ),
            ),
            (
                "match_contacts",
                ListOf(
                    valuespec=UserSelection(only_contacts=True),
                    title=_("Match contacts"),
                    help=_("The host/service must have one of the selected contacts."),
                    movable=False,
                    allow_empty=False,
                    add_label=_("Add contact"),
                ),
            ),
            (
                "match_contactgroups",
                DualListChoice(
                    title=_("Match contact groups"),
                    help=_(
                        "The host/service must be in one of the selected contact groups. This only works with Checkmk Micro Core. "
                        "If you don't use the CMC that filter will not apply"
                    ),
                    allow_empty=False,
                    choices=sorted_contact_group_choices,
                ),
            ),
            *cls._match_service_level_elements(),
            (
                "match_timeperiod",
                TimeperiodSelection(
                    title=_("Match only during time period"),
                    help=_(
                        "Match this rule only during times where the selected time period from the monitoring "
                        "system is active."
                    ),
                ),
            ),
        ]

    @classmethod
    def _match_service_level_elements(cls) -> list[DictionaryEntry]:
        if edition(paths.omd_root) is Edition.CSE:  # disabled in CSE
            return []
        return [
            (
                "match_sl",
                Tuple(
                    title=_("Match service level"),
                    help=_(
                        "Host or service must be in the following service level to get notification"
                    ),
                    orientation="horizontal",
                    show_titles=False,
                    elements=[
                        DropdownChoice(
                            label=_("from:"),
                            choices=active_config.mkeventd_service_levels,
                            prefix_values=True,
                        ),
                        DropdownChoice(
                            label=_(" to:"),
                            choices=active_config.mkeventd_service_levels,
                            prefix_values=True,
                        ),
                    ],
                ),
            )
        ]

    @abc.abstractmethod
    def _add_change(self, *, action_name: str, text: str) -> None: ...

    def _generic_rule_list_actions(
        self,
        rules: Sequence[_T_EventSpec],
        what: Literal["alert_handler", "notification"],
        what_title: str,
        save_rules: Callable[[list[_T_EventSpec]], None],
    ) -> None:
        edit_rules = list(rules)
        if request.has_var("_delete"):
            nr = request.get_integer_input_mandatory("_delete")
            self._add_change(
                action_name=what + "-delete-rule",
                text=_("Deleted %s %d") % (what_title, nr),
            )
            del edit_rules[nr]
            save_rules(edit_rules)

        elif request.has_var("_move"):
            if transactions.check_transaction():
                from_pos = request.get_integer_input_mandatory("_move")
                to_pos = request.get_integer_input_mandatory("_index")
                rule = edit_rules[from_pos]
                del edit_rules[from_pos]  # make to_pos now match!
                edit_rules[to_pos:to_pos] = [rule]
                save_rules(edit_rules)
                self._add_change(
                    action_name=what + "-move-rule",
                    text=_("Changed position of %s %d") % (what_title, from_pos),
                )


def _simple_host_rule_match_conditions() -> list[DictionaryEntry]:
    return [
        site_rule_match_condition(only_sites_with_replication=False),
        _single_folder_rule_match_condition(),
    ] + common_host_rule_match_conditions()


def _single_folder_rule_match_condition() -> DictionaryEntry:
    return (
        "match_folder",
        DropdownChoice(
            title=_("Match folder"),
            help=_(
                "This condition makes the rule match only hosts that are managed "
                "via Setup and that are contained in this folder - either directly "
                "or in one of its subfolders."
            ),
            choices=folder_tree().folder_choices,
        ),
    )


def _get_host_event_choices(add_choices: list[tuple[str, str]]) -> list[tuple[str, str]]:
    return [
        ("rd", _("UP") + " ➤ " + _("DOWN")),
        ("ru", _("UP") + " ➤ " + _("UNREACHABLE")),
        ("dr", _("DOWN") + " ➤ " + _("UP")),
        ("du", _("DOWN") + " ➤ " + _("UNREACHABLE")),
        ("ud", _("UNREACHABLE") + " ➤ " + _("DOWN")),
        ("ur", _("UNREACHABLE") + " ➤ " + _("UP")),
        ("?r", _("any") + " ➤ " + _("UP")),
        ("?d", _("any") + " ➤ " + _("DOWN")),
        ("?u", _("any") + " ➤ " + _("UNREACHABLE")),
    ] + add_choices


def _get_service_event_choices(
    flavour: Literal["notify", "alerts"], add_choices: list[tuple[str, str]]
) -> list[tuple[str, str]]:
    """Alert handler need some more options, this function is just to keep the sort order"""
    choices: list[tuple[str, str]] = [
        ("rr", _("OK") + " ➤ " + _("OK")),
        ("rw", _("OK") + " ➤ " + _("WARN")),
        ("rc", _("OK") + " ➤ " + _("CRIT")),
        ("ru", _("OK") + " ➤ " + _("UNKNOWN")),
        ("wr", _("WARN") + " ➤ " + _("OK")),
    ]

    if flavour == "alerts":
        choices += [("ww", _("WARN") + " ➤ " + _("WARN"))]

    choices += [
        ("wc", _("WARN") + " ➤ " + _("CRIT")),
        ("wu", _("WARN") + " ➤ " + _("UNKNOWN")),
        ("cr", _("CRIT") + " ➤ " + _("OK")),
        ("cw", _("CRIT") + " ➤ " + _("WARN")),
    ]

    if flavour == "alerts":
        choices += [("cc", _("CRIT") + " ➤ " + _("CRIT"))]

    choices += [
        ("cu", _("CRIT") + " ➤ " + _("UNKNOWN")),
        ("ur", _("UNKNOWN") + " ➤ " + _("OK")),
        ("uw", _("UNKNOWN") + " ➤ " + _("WARN")),
        ("uc", _("UNKNOWN") + " ➤ " + _("CRIT")),
    ]

    if flavour == "alerts":
        choices += [("uu", _("UNKNOWN") + " ➤ " + _("UNKNOWN"))]

    choices += [
        ("?r", _("any") + " ➤ " + _("OK")),
        ("?w", _("any") + " ➤ " + _("WARN")),
        ("?c", _("any") + " ➤ " + _("CRIT")),
        ("?u", _("any") + " ➤ " + _("UNKNOWN")),
    ]

    return choices + add_choices
