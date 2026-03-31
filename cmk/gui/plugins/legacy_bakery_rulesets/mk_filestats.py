#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

from collections.abc import Mapping

from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsAgentPlugins
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import (
    Alternative,
    CascadingDropdown,
    Dictionary,
    DictionaryElements,
    DropdownChoice,
    FixedValue,
    ListOf,
    Migrate,
    RegExp,
    TextInput,
    Tuple,
)
from cmk.utils.rulesets.definition import RuleGroup

PLUGIN_ONLY = "plugin_only"
WITH_CONFIGURATION = "with_configuration"


def _agent_config_mk_filestats_grouping_choices() -> list[tuple[str, str, RegExp]]:
    return [
        (
            "regex",
            _("Regular expression"),
            RegExp(
                help=_("Group files based on a regular expression pattern."),
                mode="prefix",
                allow_empty=False,
                size=70,
            ),
        ),
    ]


def _agent_config_mk_filestats_mk_filestats_section_elements() -> DictionaryElements:
    return [
        (
            "input_patterns",
            TextInput(
                title=_("Globbing pattern for input files"),
                help=_(
                    "The plug-in will process anything that is matched by this"
                    " globbing pattern. If it's a directory, recursively"
                    " process all of its content."
                ),
                allow_empty=False,
                size=70,
            ),
        ),
        (
            "filter_regex",
            TextInput(
                title=_("Filter files by matching regular expression"),
                help=_(
                    "This will result in all files whose full file path does not match"
                    " the regular expression being dismissed."
                ),
                allow_empty=False,
                size=70,
            ),
        ),
        (
            "filter_regex_inverse",
            TextInput(
                title=_("Filter files by not matching regular expression"),
                help=_(
                    "This will result in all files whose full file path does match"
                    " the regular expression being dismissed."
                ),
                allow_empty=False,
                size=70,
            ),
        ),
        (
            "filter_size",
            TextInput(
                title=_("Filter files by size"),
                help=_(
                    "This will result in all files with sizes not matching the"
                    " specification being dismissed. Specifications are in the"
                    " format [OPERATOR][SIZE_IN_BYTES], e.g. '>=1024'."
                ),
                regex="^[<=>]+[0-9]+$",
                regex_error=_("Size filter specification must be of the format [OPERATOR][INT]."),
            ),
        ),
        (
            "filter_age",
            TextInput(
                title=_("Filter files by age"),
                help=_(
                    "This will result in all files with ages not matching the"
                    " specification being dismissed. Specifications are in the"
                    " format [OPERATOR][AGE_IN_SECONDS], e.g. '>=3600'."
                ),
                regex="^[<=>]+[0-9]+$",
                regex_error=_("Age filter specification must be of the format [OPERATOR][INT]."),
            ),
        ),
        (
            "output",
            DropdownChoice(
                title=_("Output aggregation"),
                help=_(
                    "Choose what kind of output data is sent to the Checkmk server: "
                    "Only count the files, only report count and extrem files (i.e. "
                    "the oldest, newest, largest and smallest), report the "
                    "full stats on all files, or sent information about a single file only."
                ),
                choices=[
                    ("count_only", _("Count only")),
                    ("extremes_only", _("Extremes only")),
                    ("file_stats", _("Full stats")),
                    ("single_file", _("Single file")),
                ],
            ),
        ),
        (
            "grouping",
            ListOf(
                valuespec=Tuple(
                    elements=[
                        TextInput(
                            title=_("Group name"),
                            help="The section and the group name will be included in the item name."
                            " To use the single file aggregation, add <tt>%s</tt> to the group name.",
                            allow_empty=False,
                        ),
                        CascadingDropdown(
                            title=_("Grouping condition"),
                            choices=_agent_config_mk_filestats_grouping_choices(),
                        ),
                    ]
                ),
                title=_("File grouping"),
                help=_(
                    "Group files within a file group further into subgroups."
                    " Specify a name for the subgroup, and a condition by which"
                    " files are grouped. Files associated with a subgroup are"
                    " excluded from the main file group. One service is created for"
                    " each subgroup."
                ),
                magic="#groups#",
            ),
        ),
    ]


def _valuespec_agent_config_mk_filestats() -> Migrate:
    return Migrate(
        valuespec=_mk_filestats_dict(),
        migrate=_migrate_mk_filestats,
    )


def _mk_filestats_dict() -> Dictionary:
    return Dictionary(
        title=_("Count, size and age of files - mk_filestats (Linux/Solaris)"),
        help=_(
            "The agent plug-in <tt>mk_filestats</tt> monitors a configured set"
            " of files for their number, size and age. Files are grouped according"
            " to the configured section. Also a single file can be monitored."
            " If no sections are specified, the plug-in does not produce output."
        ),
        required_keys=["sections"],
        elements=[
            (
                "deployment",
                Alternative(
                    title=_("Deployment"),
                    help=_(
                        "Do not forget to activate the plug-in (i.e., deploy with or without "
                        "configuration in at least one of your rules. "
                        "It can be useful to create rules that are only partially filled out. "
                        "Since the rule execution is done on a <i>per parameter</i> base "
                        "you can for example create one rule at the top of your list that "
                        "just sets the activation to <i>no</i> for just some of your hosts without "
                        "setting any of the other parameters."
                    ),
                    elements=[
                        FixedValue(
                            value=None,
                            title=_("Do not deploy the %s plug-in") % "Filestats",
                            totext=_("(disabled)"),
                        ),
                        FixedValue(
                            value=WITH_CONFIGURATION,
                            title=_("Deploy the %s plug-in and its configuration") % "Filestats",
                            totext=_("Deploy %s") % "/etc/check_mk/filestats.cfg",
                        ),
                        FixedValue(
                            value=PLUGIN_ONLY,
                            title=_("Deploy the %s plug-in without configuration") % "Filestats",
                            help=_(
                                "The file %s needs to be created and maintained manually.<br>"
                                "Configuration entries provided with this rule will be ignored."
                            )
                            % "<tt>/etc/check_mk/filestats.cfg</tt>",
                            totext=_("manually configure %s") % "/etc/check_mk/filestats.cfg",
                        ),
                    ],
                ),
            ),
            (
                "sections",
                ListOf(
                    title="Sections",
                    valuespec=Dictionary(
                        title=_("Section of files to monitor"),
                        elements=[
                            (
                                "name",
                                TextInput(
                                    title=_("Section name"),
                                    help=_(
                                        "The section name will be included in the item name."
                                        " To use the single file aggregation, add <tt>%s</tt> to the section name."
                                    ),
                                ),
                            ),
                            *_agent_config_mk_filestats_mk_filestats_section_elements(),
                        ],
                        required_keys=["name", "input_patterns"],
                    ),
                    default_value=[{"name": "", "input_patterns": ""}],
                    magic="#sections#",
                ),
            ),
            (
                "DEFAULT",
                Dictionary(
                    title=_("Set default values for all sections"),
                    elements=_agent_config_mk_filestats_mk_filestats_section_elements(),
                    required_keys=[],
                ),
            ),
            (
                "subgroups_delimiter",
                TextInput(
                    title=_("Delimiter for file grouping"),
                    help=_(
                        "This option is only relevant if you have file grouping enabled and you wish"
                        ' to use the character "@" in any of your subgroup names.'
                        " If this is the case, please choose any ASCII character that is NOT used in any"
                        " of your subgroup names. You can also specify a combination of characters."
                        " For information: the subgroup delimiter is used to separate the subgroup name"
                        " from the main section name in the configuration file."
                        " For example: [My Subgroup@My Main Section]."
                    ),
                    default_value="@",
                ),
            ),
        ],
    )


def _migrate_mk_filestats(value: Mapping) -> Mapping:
    """
    >>> _migrate_mk_filestats({"deployment": None})
    {'sections': [], 'deployment': None}
    >>> _migrate_mk_filestats({"sections": [{"name": "", "input_patterns": ""}]})
    {'sections': [{'name': '', 'input_patterns': ''}]}
    """
    return {"sections": []} | dict(value)


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsAgentPlugins,
        name=RuleGroup.AgentConfig("mk_filestats"),
        valuespec=_valuespec_agent_config_mk_filestats,
    )
)
