#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.i18n import _
from cmk.gui.user_sites import get_activation_site_choices, get_configured_site_choices
from cmk.gui.valuespec import (
    DictionaryEntry,
    DropdownChoice,
    DualListChoice,
    Labels,
    ListOf,
    ListOfStrings,
    MonitoredHostname,
)
from cmk.gui.watolib.hosts_and_folders import folder_tree

from .._group_selection import sorted_host_group_choices
from ._rule_conditions import DictHostTagCondition


def multifolder_host_rule_match_conditions() -> list[DictionaryEntry]:
    return [
        site_rule_match_condition(only_sites_with_replication=True),
        _multi_folder_rule_match_condition(),
    ] + common_host_rule_match_conditions()


def site_rule_match_condition(only_sites_with_replication: bool) -> DictionaryEntry:
    return (
        "match_site",
        DualListChoice(
            title=_("Match sites"),
            help=_("This condition makes the rule match only hosts of the selected sites."),
            choices=(
                get_activation_site_choices
                if only_sites_with_replication
                else get_configured_site_choices
            ),
        ),
    )


def _multi_folder_rule_match_condition() -> DictionaryEntry:
    return (
        "match_folders",
        ListOf(
            valuespec=FullPathFolderChoice(
                title=_("Folder"),
                help=_(
                    "This condition makes the rule match only hosts that are managed "
                    "via Setup and that are contained in this folder - either directly "
                    "or in one of its subfolders."
                ),
            ),
            add_label=_("Add additional folder"),
            title=_("Match folders"),
            movable=False,
        ),
    )


class FullPathFolderChoice(DropdownChoice):
    def __init__(self, title: str, help: str) -> None:
        super().__init__(title=title, help=help, choices=folder_tree().folder_choices_fulltitle)


def common_host_rule_match_conditions() -> list[DictionaryEntry]:
    return [
        (
            "match_hosttags",
            DictHostTagCondition(
                title=_("Match host tags"),
                help_txt=_(
                    "Rule only applies to hosts that meet all of the host tag "
                    "conditions listed here",
                ),
            ),
        ),
        (
            "match_hostlabels",
            Labels(
                world=Labels.World.CORE,
                title=_("Match host labels"),
                help=_("Use this condition to select hosts based on the configured host labels."),
            ),
        ),
        (
            "match_hostgroups",
            DualListChoice(
                title=_("Match host groups"),
                help=_("The host must be in one of the selected host groups"),
                choices=sorted_host_group_choices,
                allow_empty=False,
            ),
        ),
        (
            "match_hosts",
            ListOfStrings(
                valuespec=MonitoredHostname(),  # type: ignore[arg-type]  # should be Valuespec[str]
                title=_("Match hosts"),
                size=24,
                orientation="horizontal",
                allow_empty=False,
                empty_text=_(
                    "Please specify at least one host. Disable the option if you want to allow all hosts."
                ),
            ),
        ),
        (
            "match_exclude_hosts",
            ListOfStrings(
                valuespec=MonitoredHostname(),  # type: ignore[arg-type]  # should be Valuespec[str]
                title=_("Exclude hosts"),
                size=24,
                orientation="horizontal",
            ),
        ),
    ]
