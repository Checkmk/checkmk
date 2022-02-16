#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    HostRulespec,
    ManualCheckParameterRulespec,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
    RulespecGroupEnforcedServicesStorage,
)
from cmk.gui.valuespec import (
    Age,
    CascadingDropdown,
    Dictionary,
    Filesize,
    Integer,
    ListOf,
    ListOfTimeRanges,
    MonitoringState,
    TextInput,
    Transform,
    Tuple,
)


def _transform_fileinfo_groups(params):
    if isinstance(params, list):
        return (
            {
                "group_patterns": params,
            }
            if params
            else {}
        )
    return params


def _get_fileinfo_groups_help():
    return _(
        "Checks <tt>fileinfo</tt> and <tt>sap_hana_fileinfo</tt> monitor "
        "the age and size of a single file. Each file information that is sent "
        "by the agent will create one service. By defining grouping "
        "patterns you can switch to checks <tt>fileinfo.groups</tt> or "
        "<tt>sap_hana_fileinfo.groups</tt>. These checks monitor a list of files at once. "
        "You can set levels not only for the total size and the age of the oldest/youngest "
        "file but also on the count. You can define one or several "
        "patterns for a group containing <tt>*</tt> and <tt>?</tt>, for example "
        "<tt>/var/log/apache/*.log</tt>. Please see Python's fnmatch for more "
        "information regarding globbing patterns and special characters. "
        "If the pattern begins with a tilde then this pattern is interpreted as "
        "a regular expression instead of as a filename globbing pattern and "
        "<tt>*</tt> and <tt>?</tt> are treated differently. "
        "For files contained in a group "
        "the discovery will automatically create a group service instead "
        "of single services for each file. This rule also applies when "
        "you use manually configured checks instead of inventorized ones. "
        "Furthermore, the current time/date in a configurable format "
        "may be included in the include pattern. The syntax is as follows: "
        "$DATE:format-spec$ or $YESTERDAY:format-spec$, where format-spec "
        "is a list of time format directives of the unix date command. "
        "Example: $DATE:%Y%m%d$ is todays date, e.g. 20140127. A pattern "
        "of /var/tmp/backups/$DATE:%Y%m%d$.txt would search for .txt files "
        "with todays date  as name in the directory /var/tmp/backups. "
        "The YESTERDAY syntax simply subtracts one day from the reference time."
    )


def _transform_level_names(conjunctions):
    """
    >>> _transform_level_names([(2, [('count', 3), ('largest_size', 8)])])
    [(2, [('count', 3), ('size_largest', 8)])]
    """
    # TODO: Investigate...
    # Trying to perform this transform directly on the CascadingDropdown resulted in rules.mk
    # not beeing update with "cmk-update-config". However after saving the rule in the GUI the
    # values were transformed...
    transform_map = {
        "largest_size": "size_largest",
        "largest_size_lower": "size_largest_lower",
        "smallest_size": "size_smallest",
        "smallest_size_lower": "size_smallest_lower",
        "oldest_age": "age_oldest",
        "oldest_age_lower": "age_oldest_lower",
        "newest_age": "age_newest",
        "newest_age_lower": "age_newest_lower",
    }
    return [
        (
            monitoring_state,
            [(transform_map.get(ident, ident), value) for ident, value in conjunction],
        )
        for monitoring_state, conjunction in conjunctions
    ]


def _valuespec_fileinfo_groups():
    return Transform(
        Dictionary(
            title=_("Group patterns"),
            elements=[
                (
                    "group_patterns",
                    ListOf(
                        Tuple(
                            help=_("This defines one file grouping pattern."),
                            show_titles=True,
                            orientation="horizontal",
                            elements=[
                                TextInput(
                                    title=_("Name of group"),
                                    size=20,
                                ),
                                Transform(
                                    Tuple(
                                        show_titles=True,
                                        orientation="vertical",
                                        elements=[
                                            TextInput(title=_("Include Pattern"), size=40),
                                            TextInput(title=_("Exclude Pattern"), size=40),
                                        ],
                                    ),
                                    forth=lambda params: isinstance(params, str)
                                    and (params, "")
                                    or params,
                                ),
                            ],
                        ),
                        title=_("File Grouping Patterns"),
                        help=_get_fileinfo_groups_help(),
                        add_label=_("Add pattern group"),
                    ),
                ),
            ],
        ),
        forth=_transform_fileinfo_groups,
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupCheckParametersStorage,
        match_type="dict",
        name="fileinfo_groups",
        valuespec=_valuespec_fileinfo_groups,
    )
)


def _item_spec_fileinfo_groups():
    return TextInput(
        title=_("File Group Name"),
        help=_(
            "This name must match the name of the group defined "
            'in the <a href="wato.py?mode=edit_ruleset&varname=fileinfo_groups">%s</a> ruleset.'
        )
        % (_("File Grouping Patterns")),
        allow_empty=True,
    )


def get_fileinfo_groups_param_elements():
    return [
        (
            "minage_oldest",
            Tuple(
                title=_("Minimal age of oldest file"),
                elements=[
                    Age(title=_("Warning below")),
                    Age(title=_("Critical below")),
                ],
            ),
        ),
        (
            "maxage_oldest",
            Tuple(
                title=_("Maximal age of oldest file"),
                elements=[
                    Age(title=_("Warning at or above")),
                    Age(title=_("Critical at or above")),
                ],
            ),
        ),
        (
            "minage_newest",
            Tuple(
                title=_("Minimal age of newest file"),
                elements=[
                    Age(title=_("Warning below")),
                    Age(title=_("Critical below")),
                ],
            ),
        ),
        (
            "maxage_newest",
            Tuple(
                title=_("Maximal age of newest file"),
                elements=[
                    Age(title=_("Warning at or above")),
                    Age(title=_("Critical at or above")),
                ],
            ),
        ),
        (
            "minsize_smallest",
            Tuple(
                title=_("Minimal size of smallest file"),
                elements=[
                    Filesize(title=_("Warning below")),
                    Filesize(title=_("Critical below")),
                ],
            ),
        ),
        (
            "maxsize_smallest",
            Tuple(
                title=_("Maximal size of smallest file"),
                elements=[
                    Filesize(title=_("Warning at or above")),
                    Filesize(title=_("Critical at or above")),
                ],
            ),
        ),
        (
            "minsize_largest",
            Tuple(
                title=_("Minimal size of largest file"),
                elements=[
                    Filesize(title=_("Warning below")),
                    Filesize(title=_("Critical below")),
                ],
            ),
        ),
        (
            "maxsize_largest",
            Tuple(
                title=_("Maximal size of largest file"),
                elements=[
                    Filesize(title=_("Warning at or above")),
                    Filesize(title=_("Critical at or above")),
                ],
            ),
        ),
        (
            "minsize",
            Tuple(
                title=_("Minimal size"),
                elements=[
                    Filesize(title=_("Warning below")),
                    Filesize(title=_("Critical below")),
                ],
            ),
        ),
        (
            "maxsize",
            Tuple(
                title=_("Maximal size"),
                elements=[
                    Filesize(title=_("Warning at or above")),
                    Filesize(title=_("Critical at or above")),
                ],
            ),
        ),
        (
            "mincount",
            Tuple(
                title=_("Minimal file count"),
                elements=[
                    Integer(title=_("Warning below")),
                    Integer(title=_("Critical below")),
                ],
            ),
        ),
        (
            "maxcount",
            Tuple(
                title=_("Maximal file count"),
                elements=[
                    Integer(title=_("Warning at or above")),
                    Integer(title=_("Critical at or above")),
                ],
            ),
        ),
        (
            "timeofday",
            ListOfTimeRanges(
                title=_("Only check during the following times of the day"),
                help=_("Outside these ranges the check will always be OK"),
            ),
        ),
        (
            "conjunctions",
            ListOf(
                Tuple(
                    elements=[
                        MonitoringState(title=_("Monitoring state"), default_value=2),
                        ListOf(
                            CascadingDropdown(
                                orientation="horizontal",
                                choices=[
                                    ("count", _("File count at"), Integer()),
                                    ("count_lower", _("File count below"), Integer()),
                                    ("size", _("File size at"), Filesize()),
                                    ("size_lower", _("File size below"), Filesize()),
                                    ("size_largest", _("Largest file size at"), Filesize()),
                                    (
                                        "size_largest_lower",
                                        _("Largest file size below"),
                                        Filesize(),
                                    ),
                                    ("size_smallest", _("Smallest file size at"), Filesize()),
                                    (
                                        "size_smallest_lower",
                                        _("Smallest file size below"),
                                        Filesize(),
                                    ),
                                    ("age_oldest", _("Oldest file age at"), Age()),
                                    ("age_oldest_lower", _("Oldest file age below"), Age()),
                                    ("age_newest", _("Newest file age at"), Age()),
                                    ("age_newest_lower", _("Newest file age below"), Age()),
                                ],
                            ),
                            magic="@#@#",
                        ),
                    ],
                ),
                title=_("Level conjunctions"),
                help=_(
                    "In order to check dependent file group statistics you can configure "
                    "conjunctions of single levels now. A conjunction consists of a monitoring state "
                    "and any number of upper or lower levels. If all of the configured levels within "
                    "a conjunction are reached then the related state is reported."
                ),
            ),
        ),
    ]


def _parameter_valuespec_fileinfo_groups() -> Dictionary:
    return Dictionary(
        elements=get_fileinfo_groups_param_elements(),
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="fileinfo-groups",
        group=RulespecGroupCheckParametersStorage,
        item_spec=_item_spec_fileinfo_groups,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_fileinfo_groups,
        title=lambda: _("Size, age and count of file groups"),
    )
)


def _transform_manual_fileinfo_groups_params(params):
    if not "group_patterns" in params:
        params["group_patterns"] = []

    return params


def _manual_parameter_valuespec_fileinfo_groups():
    return Transform(
        Dictionary(
            required_keys=["group_patterns"],
            elements=[
                (
                    "group_patterns",
                    ListOf(
                        Tuple(
                            help=_("This defines one file grouping pattern."),
                            show_titles=True,
                            orientation="vertical",
                            elements=[
                                TextInput(title=_("Include Pattern"), size=40),
                                TextInput(title=_("Exclude Pattern"), size=40),
                            ],
                        ),
                        title=_("Group patterns"),
                        help=_get_fileinfo_groups_help(),
                        add_label=_("Add pattern group"),
                    ),
                ),
            ]
            + get_fileinfo_groups_param_elements(),
        ),
        forth=_transform_manual_fileinfo_groups_params,
    )


rulespec_registry.register(
    ManualCheckParameterRulespec(
        check_group_name="fileinfo-groups",
        group=RulespecGroupEnforcedServicesStorage,
        item_spec=_item_spec_fileinfo_groups,
        parameter_valuespec=_manual_parameter_valuespec_fileinfo_groups,
        title=lambda: _("Size, age and count of file groups"),
    )
)
