#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, Integer, Percentage, TextInput, Tuple


def _parameter_valuespec_elasticsearch_indices():
    return Dictionary(
        elements=[
            (
                "elasticsearch_count_rate",
                Tuple(
                    title=_("Document count delta"),
                    help=_(
                        "If this parameter is set, the document count delta of the "
                        "last minute will be compared to the delta of the average X "
                        "minutes. You can set WARN or CRIT levels to check if the last "
                        "minute's delta is X percent higher than the average delta."
                    ),
                    elements=[
                        Percentage(title=_("Warning at"), unit=_("percent higher than average")),
                        Percentage(title=_("Critical at"), unit=_("percent higher than average")),
                        Integer(
                            title=_("Averaging"), unit=_("minutes"), minvalue=1, default_value=30
                        ),
                    ],
                ),
            ),
            (
                "elasticsearch_size_rate",
                Tuple(
                    title=_("Size delta"),
                    help=_(
                        "If this parameter is set, the size delta of the last minute "
                        "will be compared to the delta of the average X minutes. "
                        "You can set WARN or CRIT levels to check if the last minute's "
                        "delta is X percent higher than the average delta."
                    ),
                    elements=[
                        Percentage(title=_("Warning at"), unit=_("percent higher than average")),
                        Percentage(title=_("Critical at"), unit=_("percent higher than average")),
                        Integer(
                            title=_("Averaging"), unit=_("minutes"), minvalue=1, default_value=30
                        ),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="elasticsearch_indices",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(title=_("Name of indice")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_elasticsearch_indices,
        title=lambda: _("Elasticsearch Indices"),
    )
)
