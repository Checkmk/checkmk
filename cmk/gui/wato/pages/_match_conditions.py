#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

from cmk.gui.form_specs.unstable import ConditionChoices, not_empty
from cmk.gui.form_specs.unstable import Labels as FSLabels
from cmk.gui.form_specs.unstable import World as FSLabelsWorld
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
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
from cmk.gui.watolib.form_spec_generators import create_full_path_folder_choice
from cmk.gui.watolib.hosts_and_folders import folder_tree
from cmk.gui.watolib.rulesets import get_host_tags_condition_choices
from cmk.livestatus_client import SiteConfigurations
from cmk.rulesets.internal.form_specs import (
    ListOfStrings as FSListOfStrings,
)
from cmk.rulesets.internal.form_specs import (
    MultipleChoiceElementExtended,
    MultipleChoiceExtended,
    MultipleChoiceExtendedLayout,
)
from cmk.rulesets.v1 import form_specs as fs
from cmk.rulesets.v1 import Help, Label, Message, Title

from .._group_selection import sorted_host_group_choices
from ._rule_conditions import DictHostTagCondition


def multifolder_host_rule_match_conditions(
    sites: SiteConfigurations,
) -> list[DictionaryEntry]:
    return [
        site_rule_match_condition(sites, only_sites_with_replication=True),
        _multi_folder_rule_match_condition(),
    ] + common_host_rule_match_conditions()


def site_rule_match_condition(
    sites: SiteConfigurations,
    only_sites_with_replication: bool,
) -> DictionaryEntry:
    return (
        "match_site",
        DualListChoice(
            title=_("Match sites"),
            help=_("This condition makes the rule match only hosts of the selected sites."),
            choices=(
                get_activation_site_choices(sites)
                if only_sites_with_replication
                else get_configured_site_choices()
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
        super().__init__(
            title=title, help=help, choices=lambda: folder_tree().folder_choices_fulltitle(user)
        )


def common_host_rule_match_conditions() -> list[DictionaryEntry]:
    return [
        (
            "match_hosttags",
            DictHostTagCondition(
                title=_("Match host tags"),
                help_txt=_(
                    "Rule only applies to hosts that meet all of the host tag "
                    "conditions listed here.",
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


def fs_multifolder_host_rule_match_conditions(
    sites: SiteConfigurations,
) -> dict[str, fs.DictElement]:
    """FormSpec counterpart of multifolder_host_rule_match_conditions().

    The rule editor still uses the valuespec, so both have to produce the same
    stored format."""
    return {
        "match_site": fs.DictElement(
            parameter_form=MultipleChoiceExtended(
                title=Title("Match sites"),
                help_text=Help(
                    "This condition makes the rule match only hosts of the selected sites."
                ),
                elements=[
                    MultipleChoiceElementExtended(
                        name=site_id, title=Title("%(title)s") % {"title": title}
                    )
                    for site_id, title in get_activation_site_choices(sites)
                ],
                layout=MultipleChoiceExtendedLayout.dual_list,
            ),
        ),
        "match_folders": fs.DictElement(
            parameter_form=fs.List(
                title=Title("Match folders"),
                element_template=create_full_path_folder_choice(
                    title=Title("Folder"),
                    help_text=Help(
                        "This condition makes the rule match only hosts that are managed "
                        "via Setup and that are contained in this folder - either directly "
                        "or in one of its subfolders."
                    ),
                ),
                add_element_label=Label("Add additional folder"),
                editable_order=False,
            ),
        ),
        **fs_common_host_rule_match_conditions(),
    }


def fs_common_host_rule_match_conditions() -> dict[str, fs.DictElement]:
    """FormSpec counterpart of common_host_rule_match_conditions()."""
    return {
        "match_hosttags": fs.DictElement(
            parameter_form=ConditionChoices(
                title=Title("Match host tags"),
                help_text=Help(
                    "Rule only applies to hosts that meet all of the host tag "
                    "conditions listed here."
                ),
                add_condition_group_label=Label("Add tag condition"),
                select_condition_group_to_add=Label("Select tag to add"),
                no_more_condition_groups_to_add=Label("No more tags to add"),
                get_conditions=get_host_tags_condition_choices,
            ),
        ),
        "match_hostlabels": fs.DictElement(
            parameter_form=FSLabels(
                world=FSLabelsWorld.CORE,
                title=Title("Match host labels"),
                help_text=Help(
                    "Use this condition to select hosts based on the configured host labels."
                ),
            ),
        ),
        "match_hostgroups": fs.DictElement(
            parameter_form=MultipleChoiceExtended(
                title=Title("Match host groups"),
                help_text=Help("The host must be in one of the selected host groups"),
                elements=[
                    MultipleChoiceElementExtended(
                        name=group_name, title=Title("%(title)s") % {"title": title}
                    )
                    for group_name, title in sorted_host_group_choices()
                ],
                layout=MultipleChoiceExtendedLayout.dual_list,
                custom_validate=[
                    not_empty(error_msg=Message("You have to select at least one element."))
                ],
            ),
        ),
        "match_hosts": fs.DictElement(
            parameter_form=FSListOfStrings(
                title=Title("Match hosts"),
                string_spec=fs.MonitoredHost(),
                custom_validate=[
                    not_empty(
                        error_msg=Message(
                            "Please specify at least one host. Disable the option if you want to allow all hosts."
                        )
                    )
                ],
            ),
        ),
        "match_exclude_hosts": fs.DictElement(
            parameter_form=FSListOfStrings(
                title=Title("Exclude hosts"),
                string_spec=fs.MonitoredHost(),
            ),
        ),
    }
