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


def _parameter_valuespec_elasticsearch_nodes():
    return Dictionary(
        elements=[
            (
                "cpu_levels",
                Tuple(
                    title=_("Expected cpu usage"),
                    elements=[
                        Percentage(title=_("CPU usage warning at"), default_value=75.0),
                        Percentage(title=_("CPU usage critical at"), default_value=90.0),
                    ],
                ),
            ),
            (
                "open_file_descriptors",
                Tuple(
                    title=_("Expected number of open file descriptors"),
                    elements=[
                        Integer(title=_("Warning if at"), unit="file descriptors"),
                        Integer(title=_("Critical if at"), unit="file descriptor"),
                    ],
                ),
            ),
        ],
        optional_keys=["open_file_descriptors", "cpu_levels"],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="elasticsearch_nodes",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(title=_("Name of node")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_elasticsearch_nodes,
        title=lambda: _("Elasticsearch Nodes"),
    )
)
