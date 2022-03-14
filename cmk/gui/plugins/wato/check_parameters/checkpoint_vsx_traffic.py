#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    Levels,
    rulespec_registry,
    RulespecGroupCheckParametersNetworking,
)
from cmk.gui.valuespec import Dictionary, TextInput


def _parameter_valuespec_checkpoint_vsx_traffic():
    return Dictionary(
        elements=[
            (
                "bytes_accepted",
                Levels(
                    title=_("Maximum rate of bytes accepted"),
                    default_value=None,
                    default_levels=(100000, 200000),
                    unit="bytes/sec",
                ),
            ),
            (
                "bytes_dropped",
                Levels(
                    title=_("Maximum rate of bytes dropped"),
                    default_value=None,
                    default_levels=(100000, 200000),
                    unit="bytes/sec",
                ),
            ),
            (
                "bytes_rejected",
                Levels(
                    title=_("Maximum rate of bytes rejected"),
                    default_value=None,
                    default_levels=(100000, 200000),
                    unit="bytes/sec",
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="checkpoint_vsx_traffic",
        group=RulespecGroupCheckParametersNetworking,
        item_spec=lambda: TextInput(title=_("VSID")),
        parameter_valuespec=_parameter_valuespec_checkpoint_vsx_traffic,
        title=lambda: _("Checkpoint VSID traffic rate"),
    )
)
