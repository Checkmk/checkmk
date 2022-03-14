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
from cmk.gui.valuespec import Dictionary, Filesize, Float, Integer, TextInput, Tuple


def _parameter_valuespec_rabbitmq_nodes_gc():
    return Dictionary(
        elements=[
            (
                "gc_num_upper",
                Tuple(
                    title=_("Upper level for total number of GC runs"),
                    elements=[
                        Integer(title=_("Warning at"), unit="runs"),
                        Integer(title=_("Critical at"), unit="runs"),
                    ],
                ),
            ),
            (
                "gc_num_rate_upper",
                Tuple(
                    title=_("Upper level for GC run rate"),
                    elements=[
                        Float(title=_("Warning at"), unit="1/s"),
                        Float(title=_("Critical at"), unit="1/s"),
                    ],
                ),
            ),
            (
                "gc_num_rate_lower",
                Tuple(
                    title=_("Lower level for GC run rate"),
                    elements=[
                        Float(title=_("Warning below"), unit="1/s"),
                        Float(title=_("Critical below"), unit="1/s"),
                    ],
                ),
            ),
            (
                "gc_bytes_reclaimed_upper",
                Tuple(
                    title=_("Absolute levels for memory reclaimed by GC"),
                    elements=[
                        Filesize(title=_("Warning at")),
                        Filesize(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "gc_bytes_reclaimed_rate_upper",
                Tuple(
                    title=_("Upper level for rate of memory reclaimed by GC"),
                    elements=[
                        Filesize(title=_("Warning at"), unit="1/s"),
                        Filesize(title=_("Critical at"), unit="1/s"),
                    ],
                ),
            ),
            (
                "gc_bytes_reclaimed_rate_lower",
                Tuple(
                    title=_("Lower level for rate of memory reclaimed by GC"),
                    elements=[
                        Filesize(title=_("Warning below"), unit="1/s"),
                        Filesize(title=_("Critical below"), unit="1/s"),
                    ],
                ),
            ),
            (
                "runqueue_upper",
                Tuple(
                    title=_("Upper level for runtime run queue"),
                    elements=[
                        Integer(title=_("Warning at")),
                        Integer(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "runqueue_lower",
                Tuple(
                    title=_("Lower level for runtime run queue"),
                    elements=[
                        Integer(title=_("Warning below")),
                        Integer(title=_("Critical below")),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="rabbitmq_nodes_gc",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(title=_("Node name")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_rabbitmq_nodes_gc,
        title=lambda: _("RabbitMQ nodes GC"),
    )
)
