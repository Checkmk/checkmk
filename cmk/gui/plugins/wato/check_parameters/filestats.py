#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import List, Tuple as _Tuple
from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Age,
    Checkbox,
    Dictionary,
    Filesize,
    Integer,
    ListOf,
    RegExpUnicode,
    TextAscii,
    Tuple,
    ValueSpec,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)

file_size_age_elements: List[_Tuple[str, ValueSpec]] = [
    ("minage_oldest",
     Tuple(
         title=_("Minimal age of oldest file"),
         elements=[
             Age(title=_("Warning if younger than")),
             Age(title=_("Critical if younger than")),
         ],
     )),
    ("maxage_oldest",
     Tuple(
         title=_("Maximal age of oldest file"),
         elements=[
             Age(title=_("Warning if older than")),
             Age(title=_("Critical if older than")),
         ],
     )),
    ("minage_newest",
     Tuple(
         title=_("Minimal age of newest file"),
         elements=[
             Age(title=_("Warning if younger than")),
             Age(title=_("Critical if younger than")),
         ],
     )),
    ("maxage_newest",
     Tuple(
         title=_("Maximal age of newest file"),
         elements=[
             Age(title=_("Warning if older than")),
             Age(title=_("Critical if older than")),
         ],
     )),
    ("minsize_smallest",
     Tuple(
         title=_("Minimal size of smallest file"),
         elements=[
             Filesize(title=_("Warning if below")),
             Filesize(title=_("Critical if below")),
         ],
     )),
    ("maxsize_smallest",
     Tuple(
         title=_("Maximal size of smallest file"),
         elements=[
             Filesize(title=_("Warning if above")),
             Filesize(title=_("Critical if above")),
         ],
     )),
    ("minsize_largest",
     Tuple(
         title=_("Minimal size of largest file"),
         elements=[
             Filesize(title=_("Warning if below")),
             Filesize(title=_("Critical if below")),
         ],
     )),
    ("maxsize_largest",
     Tuple(
         title=_("Maximal size of largest file"),
         elements=[
             Filesize(title=_("Warning if above")),
             Filesize(title=_("Critical if above")),
         ],
     )),
]


def _item_spec_filestats():
    return TextAscii(title=_("File Group Name"),
                     help=_("This name must match the name of the section defined "
                            "in the mk_filestats configuration."),
                     allow_empty=True)


def _parameter_valuespec_filestats():
    return Dictionary(
        elements=file_size_age_elements + [
            ("mincount",
             Tuple(
                 title=_("Minimal file count"),
                 elements=[
                     Integer(title=_("Warning if below")),
                     Integer(title=_("Critical if below")),
                 ],
             )),
            ("maxcount",
             Tuple(
                 title=_("Maximal file count"),
                 elements=[
                     Integer(title=_("Warning if above")),
                     Integer(title=_("Critical if above")),
                 ],
             )),
            ("show_all_files",
             Checkbox(title=_("Show all files in long output"), label=("Show files"))),
            ("additional_rules",
             ListOf(Tuple(elements=[
                 RegExpUnicode(title=_("Filename/- expression"), mode="case_sensitive"),
                 Dictionary(elements=file_size_age_elements),
             ],),
                    title=_("Additional rules for files"),
                    help=_("You can specify a filename or a regular expresion, and additional "
                           "rules that are applied to the matching files. This means that the "
                           "rules set for the whole file group are overwritten for those files. "
                           "Note that the order in which you specify the rules matters: "
                           "in case of multiple matching rules, the first matching rule is "
                           "applied."))),
        ],
        help=_("Here you can impose various levels on the results reported by the"
               " mk_filstats plugin. Note that some levels only apply to a matching"
               " output format (e.g. max/min count levels are not applied if only the"
               " smallest, largest, oldest and newest file is reported). In order to"
               " receive the required data, you must configure the plugin mk_filestats."),
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="filestats",
        group=RulespecGroupCheckParametersStorage,
        item_spec=_item_spec_filestats,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_filestats,
        title=lambda: _("Size, age and count of file groups (mk_filestats)"),
    ))
