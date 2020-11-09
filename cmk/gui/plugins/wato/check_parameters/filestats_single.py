#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Dictionary,
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


def _item_spec_filestats():
    return TextAscii(title=_("File Name"),
                     help=_("This name corresponds to the single file name to be monitored."),
                     allow_empty=True)


def _parameter_valuespec_filestats():
    return Dictionary(
        elements=[
            ('min_age', min_age_levels()),
            ('max_age', max_age_levels()),
            ('min_size', min_size_levels()),
            ('max_size', max_size_levels()),
        ],
        help=_("Here you can impose various levels the results reported by the"
               " mk_filstats plugin. Note that those levels only concern about a single file."),
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="filestats_single",
        group=RulespecGroupCheckParametersStorage,
        item_spec=_item_spec_filestats,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_filestats,
        title=lambda: _("Size and age of a single file (mk_filestats)"),
    ))
