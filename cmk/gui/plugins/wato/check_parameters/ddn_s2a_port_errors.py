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
from cmk.gui.valuespec import Dictionary, Integer, TextInput, Tuple


def _parameter_valuespec_ddn_s2a_port_errors() -> Dictionary:
    return Dictionary(
        elements=[
            (
                "link_failure_errs",
                Tuple(
                    title=_("Link failure errors"),
                    elements=[
                        Integer(title=_("Warning at")),
                        Integer(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "lost_sync_errs",
                Tuple(
                    title=_("Lost synchronization errors"),
                    elements=[
                        Integer(title=_("Warning at")),
                        Integer(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "loss_of_signal_errs",
                Tuple(
                    title=_("Loss of signal errors"),
                    elements=[
                        Integer(title=_("Warning at")),
                        Integer(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "prim_seq_errs",
                Tuple(
                    title=_("PrimSeq erros"),
                    elements=[
                        Integer(title=_("Warning at")),
                        Integer(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "crc_errs",
                Tuple(
                    title=_("CRC errors"),
                    elements=[
                        Integer(title=_("Warning at")),
                        Integer(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "receive_errs",
                Tuple(
                    title=_("Receive errors"),
                    elements=[
                        Integer(title=_("Warning at")),
                        Integer(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "ctio_timeouts",
                Tuple(
                    title=_("CTIO timeouts"),
                    elements=[
                        Integer(title=_("Warning at")),
                        Integer(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "ctio_xmit_errs",
                Tuple(
                    title=_("CTIO transmission errors"),
                    elements=[
                        Integer(title=_("Warning at")),
                        Integer(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "ctio_other_errs",
                Tuple(
                    title=_("other CTIO errors"),
                    elements=[
                        Integer(title=_("Warning at")),
                        Integer(title=_("Critical at")),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="ddn_s2a_port_errors",
        group=RulespecGroupCheckParametersStorage,
        item_spec=lambda: TextInput(title="Port index"),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_ddn_s2a_port_errors,
        title=lambda: _("DDN S2A port errors"),
    )
)
