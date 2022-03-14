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
    RulespecGroupCheckParametersStorage,
)
from cmk.gui.valuespec import Dictionary, TextInput


def _parameter_valuespec_fcport_words():
    return Dictionary(
        title=_("Levels for transmitted and received words"),
        elements=[
            ("fc_tx_words", Levels(title=_("Tx"), unit=_("words/s"))),
            ("fc_rx_words", Levels(title=_("Rx"), unit=_("words/s"))),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="fcport_words",
        group=RulespecGroupCheckParametersStorage,
        item_spec=lambda: TextInput(
            title=_("Port index"),
        ),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_fcport_words,
        title=lambda: _("Atto Fibrebridge FC port"),
    )
)
