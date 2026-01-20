#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)
from cmk.gui.valuespec import Dictionary, Float, Migrate, Percentage, TextInput, Transform, Tuple

_MS_KEY_MAP = {
    "write_avg_exe_ms": "write_avg_exe_s",
    "write_avg_rtt_ms": "write_avg_rtt_s",
    "read_avg_exe_ms": "read_avg_exe_s",
    "read_avg_rtt_ms": "read_avg_rtt_s",
}


def _ms_to_s(v: float) -> float:
    return v / 1000.0


def _s_to_ms(v: float) -> float:
    return v * 1000.0


def _migrate_milliseconds(spec: dict[str, Any]) -> dict[str, Any]:
    if "read_avg_rtt_s" in spec:
        return spec

    return {
        _MS_KEY_MAP.get(k, k): (_ms_to_s(v[0]), _ms_to_s(v[1])) if k in _MS_KEY_MAP else v
        for k, v in spec.items()
    }


def _parameter_valuespec_nfsiostats() -> Migrate[dict[str, Any]]:
    return Migrate(
        migrate=_migrate_milliseconds,
        valuespec=Dictionary(
            title=_("NFS IO statistics"),
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
                        title=_("RPC backlog"),
                        elements=[
                            Float(title=_("Warning below"), unit="queue"),
                            Float(title=_("Critical below"), unit="queue"),
                        ],
                    ),
                ),
                (
                    "read_ops",
                    Tuple(
                        title=_("Read operations /s"),
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
                        title=_("Read retransmissions"),
                        elements=[
                            Percentage(title=_("Warning at")),
                            Percentage(title=_("Critical at")),
                        ],
                    ),
                ),
                (
                    "read_avg_rtt_s",
                    Tuple(
                        title=_("Read average RTT (ms)"),
                        elements=[
                            Transform(
                                valuespec=Float(title=_("Warning at"), unit="ms"),
                                from_valuespec=_ms_to_s,
                                to_valuespec=_s_to_ms,
                            ),
                            Transform(
                                valuespec=Float(title=_("Critical at"), unit="ms"),
                                from_valuespec=_ms_to_s,
                                to_valuespec=_s_to_ms,
                            ),
                        ],
                    ),
                ),
                (
                    "read_avg_exe_s",
                    Tuple(
                        title=_("Read average executions (ms)"),
                        elements=[
                            Transform(
                                valuespec=Float(title=_("Warning at"), unit="ms"),
                                from_valuespec=_ms_to_s,
                                to_valuespec=_s_to_ms,
                            ),
                            Transform(
                                valuespec=Float(title=_("Critical at"), unit="ms"),
                                from_valuespec=_ms_to_s,
                                to_valuespec=_s_to_ms,
                            ),
                        ],
                    ),
                ),
                (
                    "write_ops_s",
                    Tuple(
                        title=_("Write operations/s"),
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
                        title=_("Write retransmissions"),
                        elements=[
                            Percentage(title=_("Warning at")),
                            Percentage(title=_("Critical at")),
                        ],
                    ),
                ),
                (
                    "write_avg_rtt_s",
                    Tuple(
                        title=_("Write avg RTT (ms)"),
                        elements=[
                            Transform(
                                valuespec=Float(title=_("Warning at"), unit="ms"),
                                from_valuespec=_ms_to_s,
                                to_valuespec=_s_to_ms,
                            ),
                            Transform(
                                valuespec=Float(title=_("Critical at"), unit="ms"),
                                from_valuespec=_ms_to_s,
                                to_valuespec=_s_to_ms,
                            ),
                        ],
                    ),
                ),
                (
                    "write_avg_exe_s",
                    Tuple(
                        title=_("Write avg exe (ms)"),
                        elements=[
                            Transform(
                                valuespec=Float(title=_("Warning at"), unit="ms"),
                                from_valuespec=_ms_to_s,
                                to_valuespec=_s_to_ms,
                            ),
                            Transform(
                                valuespec=Float(title=_("Critical at"), unit="ms"),
                                from_valuespec=_ms_to_s,
                                to_valuespec=_s_to_ms,
                            ),
                        ],
                    ),
                ),
            ],
        ),
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="nfsiostats",
        group=RulespecGroupCheckParametersStorage,
        item_spec=lambda: TextInput(
            title=_("NFS IO statistics"),
        ),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_nfsiostats,
        title=lambda: _("NFS IO statistics"),
    )
)
