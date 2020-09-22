#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Tuple,
    Age,
    Filesize,
    ListOf,
    RegExpUnicode,
    Dictionary,
)


def min_age_levels():
    return Tuple(
        title=_("Minimal age of a file"),
        elements=[
            Age(title=_("Warning if younger than")),
            Age(title=_("Critical if younger than")),
        ],
    )


def max_age_levels():
    return Tuple(
        title=_("Maximal age of a file"),
        elements=[
            Age(title=_("Warning if older than")),
            Age(title=_("Critical if older than")),
        ],
    )


def min_size_levels():
    return Tuple(
        title=_("Minimal size of a file"),
        elements=[
            Filesize(title=_("Warning if below")),
            Filesize(title=_("Critical if below")),
        ],
    )


def max_size_levels():
    return Tuple(
        title=_("Maximal size of a file"),
        elements=[
            Filesize(title=_("Warning if above")),
            Filesize(title=_("Critical if above")),
        ],
    )


def additional_rules(maxage_name, minage_name, maxsize_name, minsize_name):
    return "additional_rules", ListOf(
        Tuple(elements=[
            RegExpUnicode(title=_("Filename/- expression"), mode="case_sensitive"),
            Dictionary(elements=[
                (maxage_name, max_age_levels()),
                (minage_name, min_age_levels()),
                (maxsize_name, max_size_levels()),
                (minsize_name, min_size_levels()),
            ]),
        ],),
        title=_("Additional rules for files"),
        help=_("You can specify a filename or a regular expresion, and additional "
               "rules that are applied to the matching files. This means that the "
               "rules set for the whole file group are overwritten for those files. "
               "Note that the order in which you specify the rules matters: "
               "in case of multiple matching rules, the first matching rule is "
               "applied."))
