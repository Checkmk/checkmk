#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)
from cmk.gui.valuespec import Age, Dictionary, Filesize, TextInput, Tuple


def _item_spec_filestats():
    return TextInput(
        title=_("File name"),
        help=_("This name corresponds to the single file name to be monitored."),
        allow_empty=True,
        try_max_width=True,
    )


def _parameter_valuespec_filestats():
    return Dictionary(
        elements=[
            (
                "min_age",
                Tuple(
                    title=_("Minimal age of a file"),
                    elements=[
                        Age(title=_("Warning below")),
                        Age(title=_("Critical below")),
                    ],
                ),
            ),
            (
                "max_age",
                Tuple(
                    title=_("Maximal age of a file"),
                    elements=[
                        Age(title=_("Warning at or above")),
                        Age(title=_("Critical at or above")),
                    ],
                ),
            ),
            (
                "min_size",
                Tuple(
                    title=_("Minimal size of a file"),
                    elements=[
                        Filesize(title=_("Warning below")),
                        Filesize(title=_("Critical below")),
                    ],
                ),
            ),
            (
                "max_size",
                Tuple(
                    title=_("Maximal size of a file"),
                    elements=[
                        Filesize(title=_("Warning at or above")),
                        Filesize(title=_("Critical at or above")),
                    ],
                ),
            ),
        ],
        help=_(
            "Here you can impose various levels the results reported by the"
            " mk_filstats plugin. Note that those levels only concern about a single file."
        ),
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="filestats_single",
        group=RulespecGroupCheckParametersStorage,
        item_spec=_item_spec_filestats,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_filestats,
        title=lambda: _("Size and age of a single file (mk_filestats)"),
    )
)
