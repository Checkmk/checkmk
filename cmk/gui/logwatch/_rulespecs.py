#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.search import MatchItemGeneratorRegistry
from cmk.gui.valuespec import (
    Dictionary,
    DropdownChoice,
    ListOf,
    RegExp,
    TextInput,
    Tuple,
)
from cmk.gui.wato.pages import pattern_editor
from cmk.gui.watolib.mode import ModeRegistry
from cmk.gui.watolib.rulespec_groups import (
    RulespecGroupCheckParametersApplications,
    RulespecGroupCheckParametersDiscovery,
)
from cmk.gui.watolib.rulespecs import (
    HostRulespec,
    RulespecRegistry,
    ServiceRulespec,
)
from cmk.utils.rulesets.definition import RuleGroup


def register(
    rulespec_registry: RulespecRegistry,
    mode_registry: ModeRegistry,
    match_item_generator_registry: MatchItemGeneratorRegistry,
) -> None:
    rulespec_registry.register(
        ServiceRulespec(
            group=RulespecGroupCheckParametersApplications,
            item_help=_item_help_logwatch_rules,
            item_name=lambda: _("Log file"),
            item_type="item",
            match_type="all",
            name="logwatch_rules",
            valuespec=_valuespec_logwatch_rules,
        )
    )
    rulespec_registry.register(
        HostRulespec(
            group=RulespecGroupCheckParametersDiscovery,
            match_type="all",
            name=RuleGroup.DiscoveryParameters("logwatch_groups"),
            valuespec=_valuespec_logwatch_groups,
        )
    )
    pattern_editor.register(mode_registry, match_item_generator_registry)


def _item_help_logwatch_rules() -> str:
    return _(
        'Put the item names of the log files here. For example "System$" '
        'to select the service "LOG System". You can use regular '
        "expressions which must match the beginning of the log file name."
    )


def _valuespec_logwatch_rules() -> Dictionary:
    return Dictionary(
        title=_("Log file patterns"),
        elements=[
            (
                "reclassify_patterns",
                ListOf(
                    valuespec=Tuple(
                        help=_("This defines one log file pattern rule"),
                        show_titles=True,
                        orientation="horizontal",
                        elements=[
                            DropdownChoice(
                                title=_("State"),
                                choices=[
                                    ("C", _("CRITICAL")),
                                    ("W", _("WARNING")),
                                    ("O", _("OK")),
                                    ("I", _("IGNORE")),
                                ],
                            ),
                            RegExp(title=_("Pattern (Regex)"), size=40, mode=RegExp.infix),
                            TextInput(title=_("Comment"), size=40),
                        ],
                    ),
                    title=_("Reclassify state matching regex pattern"),
                    help=_(
                        "<p>You can define one or several patterns (regular expressions) in each logfile pattern rule. "
                        "These patterns are applied to the selected logfiles to reclassify the "
                        "matching log messages. The first pattern which matches a line will "
                        "be used for reclassifying a message. You can use the "
                        '<a href="wato.py?mode=pattern_editor">Logfile pattern analyzer</a> '
                        "to test the rules you defined here.</p>"
                        "<p>Note that to match a special regex character in your patterns, you need to use a "
                        "backslash to escape its special meaning. This is especially relevant for Windows file paths. "
                        'For example, to match the Windows path "C:\\Users\\amdin\\Desktop", enter '
                        '"C:\\\\Users\\\\admin\\\\Desktop".</p>'
                        '<p>Select "Ignore" as state to get the matching logs deleted. Other states will keep the '
                        "log entries but reclassify the state of them.</p>"
                    ),
                    add_label=_("Add pattern"),
                ),
            ),
            (
                "reclassify_states",
                Dictionary(
                    title=_("Reclassify complete state"),
                    help=_(
                        "This setting allows you to convert all incoming states to another state. "
                        "The option is applied before the state conversion via regexes. So the regex values can "
                        "modify the state even further."
                    ),
                    elements=[
                        (
                            "c_to",
                            DropdownChoice(
                                title=_("Change CRITICAL state to"),
                                choices=[
                                    ("C", _("CRITICAL")),
                                    ("W", _("WARNING")),
                                    ("O", _("OK")),
                                    ("I", _("IGNORE")),
                                    (".", _("Context info")),
                                ],
                                default_value="C",
                            ),
                        ),
                        (
                            "w_to",
                            DropdownChoice(
                                title=_("Change WARNING state to"),
                                choices=[
                                    ("C", _("CRITICAL")),
                                    ("W", _("WARNING")),
                                    ("O", _("OK")),
                                    ("I", _("IGNORE")),
                                    (".", _("Context info")),
                                ],
                                default_value="W",
                            ),
                        ),
                        (
                            "o_to",
                            DropdownChoice(
                                title=_("Change OK state to"),
                                choices=[
                                    ("C", _("CRITICAL")),
                                    ("W", _("WARNING")),
                                    ("O", _("OK")),
                                    ("I", _("IGNORE")),
                                    (".", _("Context info")),
                                ],
                                default_value="O",
                            ),
                        ),
                        (
                            "._to",
                            DropdownChoice(
                                title=_("Change context info to"),
                                choices=[
                                    ("C", _("CRITICAL")),
                                    ("W", _("WARNING")),
                                    ("O", _("OK")),
                                    ("I", _("IGNORE")),
                                    (".", _("Context info")),
                                ],
                                default_value=".",
                            ),
                        ),
                    ],
                    optional_keys=False,
                ),
            ),
        ],
        optional_keys=["reclassify_states"],
        ignored_keys=["pre_comp_group_patterns", "group_patterns"],
    )


def _valuespec_logwatch_groups() -> Dictionary:
    return Dictionary(
        title=_("Log file grouping"),
        elements=[
            (
                "grouping_patterns",
                ListOf(
                    valuespec=Tuple(
                        help=_("This defines one log file grouping pattern"),
                        show_titles=True,
                        orientation="horizontal",
                        elements=[
                            TextInput(
                                title=_("Name of group"),
                            ),
                            Tuple(
                                show_titles=True,
                                orientation="vertical",
                                elements=[
                                    TextInput(title=_("Include pattern")),
                                    TextInput(title=_("Exclude pattern")),
                                ],
                            ),
                        ],
                    ),
                    add_label=_("Add pattern group"),
                    title=_("List grouping patterns"),
                ),
            ),
        ],
        optional_keys=[],
        help=_(
            "The check <tt>Logwatch</tt> normally creates one service for each log file. "
            "By defining grouping patterns you can switch to the check "
            "<tt>logwatch.groups</tt>. If the pattern begins with a tilde then this "
            "pattern is interpreted as a regular expression instead of as a file name "
            "globbing pattern and <tt>*</tt> and <tt>?</tt> are treated differently. "
            "That check monitors a list of log files at once. This is useful if you "
            "have e.g. a folder with rotated log files where the name of the current "
            "log file also changes with each rotation."
        ),
    )
