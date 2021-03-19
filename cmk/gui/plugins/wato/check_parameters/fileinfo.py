#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Age,
    Dictionary,
    Filesize,
    ListOfTimeRanges,
    MonitoringState,
    TextAscii,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)


def _parameter_valuespec_fileinfo():
    return Dictionary(elements=[
        ("minage",
         Tuple(
             title=_("Minimal age"),
             elements=[
                 Age(title=_("Warning if younger than")),
                 Age(title=_("Critical if younger than")),
             ],
         )),
        ("maxage",
         Tuple(
             title=_("Maximal age"),
             elements=[
                 Age(title=_("Warning if older than")),
                 Age(title=_("Critical if older than")),
             ],
         )),
        ("minsize",
         Tuple(
             title=_("Minimal size"),
             elements=[
                 Filesize(title=_("Warning if below")),
                 Filesize(title=_("Critical if below")),
             ],
         )),
        ("maxsize",
         Tuple(
             title=_("Maximal size"),
             elements=[
                 Filesize(title=_("Warning at")),
                 Filesize(title=_("Critical at")),
             ],
         )),
        ("timeofday",
         ListOfTimeRanges(
             title=_("Only check during the following times of the day"),
             help=_("Outside these ranges the check will always be OK"),
         )),
        ("state_missing", MonitoringState(default_value=3, title=_("State when file is missing"))),
    ],)


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="fileinfo",
        group=RulespecGroupCheckParametersStorage,
        item_spec=lambda: TextAscii(title=_("File name"), allow_empty=True),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_fileinfo,
        title=lambda: _("Size and age of single files"),
    ))
