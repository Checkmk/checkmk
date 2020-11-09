#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Dictionary,
    ListOfTimeRanges,
    MonitoringState,
    TextAscii,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)

from cmk.gui.plugins.wato.check_parameters.file_attributes_utils import (
    min_age_levels,
    max_age_levels,
    min_size_levels,
    max_size_levels,
)


def _parameter_valuespec_fileinfo():
    return Dictionary(elements=[
        ("minage", min_age_levels()),
        ("maxage", max_age_levels()),
        ("minsize", min_size_levels()),
        ("maxsize", max_size_levels()),
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
