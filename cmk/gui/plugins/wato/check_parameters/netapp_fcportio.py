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
from cmk.gui.valuespec import Dictionary, Filesize, TextInput, Tuple


def _parameter_valuespec_netapp_fcportio():
    return Dictionary(
        elements=[
            (
                "read",
                Tuple(
                    title=_("Read"),
                    elements=[
                        Filesize(title=_("Warning if below")),
                        Filesize(title=_("Critical if below")),
                    ],
                ),
            ),
            (
                "write",
                Tuple(
                    title=_("Write"),
                    elements=[
                        Filesize(title=_("Warning at")),
                        Filesize(title=_("Critical at")),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="netapp_fcportio",
        group=RulespecGroupCheckParametersStorage,
        item_spec=lambda: TextInput(title=_("File name"), allow_empty=True),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_netapp_fcportio,
        title=lambda: _("Netapp FC Port throughput"),
    )
)
