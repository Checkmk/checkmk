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
from cmk.gui.valuespec import Dictionary, Float, Percentage, TextInput, Tuple


def _parameter_valuespec_nfsiostats():
    return Dictionary(
        title=_("NFS IO Statistics"),
        optional_keys=True,
        elements=[
            (
                "op_s",
                Tuple(
                    title=_("Operations"),
                    elements=[
                        Float(title=_("Warning at"), unit="1/s"),
                        Float(title=_("Critical at"), unit="1/s"),
                    ],
                ),
            ),
            (
                "rpc_backlog",
                Tuple(
                    title=_("RPC Backlog"),
                    elements=[
                        Float(title=_("Warning below"), unit="queue"),
                        Float(title=_("Critical below"), unit="queue"),
                    ],
                ),
            ),
            (
                "read_ops",
                Tuple(
                    title=_("Read Operations /s"),
                    elements=[
                        Float(title=_("Warning at"), unit="1/s"),
                        Float(title=_("Critical at"), unit="1/s"),
                    ],
                ),
            ),
            (
                "read_b_s",
                Tuple(
                    title=_("Reads size /s"),
                    elements=[
                        Float(title=_("Warning at"), unit="bytes/s"),
                        Float(title=_("Critical at"), unit="bytes/s"),
                    ],
                ),
            ),
            (
                "read_b_op",
                Tuple(
                    title=_("Read bytes per operation"),
                    elements=[
                        Float(title=_("Warning at"), unit="bytes/op"),
                        Float(title=_("Critical at"), unit="bytes/op"),
                    ],
                ),
            ),
            (
                "read_retrans",
                Tuple(
                    title=_("Read Retransmissions"),
                    elements=[
                        Percentage(title=_("Warning at")),
                        Percentage(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "read_avg_rtt_ms",
                Tuple(
                    title=_("Read Average RTT (ms)"),
                    elements=[
                        Float(title=_("Warning at"), unit="ms"),
                        Float(title=_("Critical at"), unit="ms"),
                    ],
                ),
            ),
            (
                "read_avg_exe_ms",
                Tuple(
                    title=_("Read Average Executions (ms)"),
                    elements=[
                        Float(title=_("Warning at"), unit="ms"),
                        Float(title=_("Critical at"), unit="ms"),
                    ],
                ),
            ),
            (
                "write_ops_s",
                Tuple(
                    title=_("Write Operations/s"),
                    elements=[
                        Float(title=_("Warning at"), unit="1/s"),
                        Float(title=_("Critical at"), unit="1/s"),
                    ],
                ),
            ),
            (
                "write_b_s",
                Tuple(
                    title=_("Write size /s"),
                    elements=[
                        Float(title=_("Warning at"), unit="bytes/s"),
                        Float(title=_("Critical at"), unit="bytes/s"),
                    ],
                ),
            ),
            (
                "write_b_op",
                Tuple(
                    title=_("Write bytes per operation"),
                    elements=[
                        Float(title=_("Warning at"), unit="bytes/s"),
                        Float(title=_("Critical at"), unit="bytes/s"),
                    ],
                ),
            ),
            (
                "write_retrans",
                Tuple(
                    title=_("Write Retransmissions"),
                    elements=[
                        Percentage(title=_("Warning at")),
                        Percentage(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "write_avg_rtt_ms",
                Tuple(
                    title=_("Write Avg RTT (ms)"),
                    elements=[
                        Float(title=_("Warning at"), unit="ms"),
                        Float(title=_("Critical at"), unit="ms"),
                    ],
                ),
            ),
            (
                "write_avg_exe_ms",
                Tuple(
                    title=_("Write Avg exe (ms)"),
                    elements=[
                        Float(title=_("Warning at"), unit="ms"),
                        Float(title=_("Critical at"), unit="ms"),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="nfsiostats",
        group=RulespecGroupCheckParametersStorage,
        item_spec=lambda: TextInput(
            title=_("NFS IO Statistics"),
        ),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_nfsiostats,
        title=lambda: _("NFS IO Statistics"),
    )
)
