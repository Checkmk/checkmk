#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import List
from typing import Tuple as _Tuple

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)
from cmk.gui.valuespec import (
    Age,
    Checkbox,
    Dictionary,
    Filesize,
    Integer,
    ListOf,
    RegExp,
    TextInput,
    Tuple,
    ValueSpec,
)

file_size_age_elements: List[_Tuple[str, ValueSpec]] = [
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
]


def _item_spec_filestats():
    return TextInput(
        title=_("File Group Name"),
        help=_(
            "This name must match the name of the section defined "
            "in the mk_filestats configuration."
        ),
        allow_empty=True,
    )


def _parameter_valuespec_filestats():
    return Dictionary(
        elements=file_size_age_elements
        + [
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
                "show_all_files",
                Checkbox(
                    title=_("Show files in service details"),
                    label=("Show files"),
                    help=_(
                        "Display all files that have reached a WARN or a CRIT status in the "
                        "service details. Note: displaying the files leads to a performance loss "
                        "for large numbers of files within the file group. Please enable this feature "
                        "only if it is needed."
                    ),
                ),
            ),
            (
                "additional_rules",
                ListOf(
                    valuespec=Tuple(
                        elements=[
                            TextInput(
                                title=_("Display name"),
                                help=_(
                                    "Specify a user-friendly name that will be displayed in the service "
                                    "details, along with the pattern to match."
                                ),
                            ),
                            RegExp(
                                title=_("Filename/- expression"),
                                mode="infix",
                                size=70,
                            ),
                            Dictionary(elements=file_size_age_elements),
                        ],
                    ),
                    title=_("Additional rules for outliers"),
                    help=_(
                        "This feature is to apply different rules to files that are "
                        "inconsistent with the files expected in this file group. "
                        "This means that the rules set for the file group are overwritten. "
                        "You can specify a filename or a regular expresion, and additional "
                        "rules that are applied to the matching files. In case of multiple "
                        "matching rules, the first matching rule is applied. "
                        "Note: this feature is intended for outliers, and is therefore not "
                        "suitable to configure subgroups. "
                    ),
                ),
            ),
        ],
        help=_(
            "Here you can impose various levels on the results reported by the"
            " mk_filstats plugin. Note that some levels only apply to a matching"
            " output format (e.g. max/min count levels are not applied if only the"
            " smallest, largest, oldest and newest file is reported). In order to"
            " receive the required data, you must configure the plugin mk_filestats."
        ),
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="filestats",
        group=RulespecGroupCheckParametersStorage,
        item_spec=_item_spec_filestats,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_filestats,
        title=lambda: _("Size, age and count of file groups (mk_filestats)"),
    )
)
