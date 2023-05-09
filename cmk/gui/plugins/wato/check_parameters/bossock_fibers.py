#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Integer,
    TextAscii,
    Tuple,
)
from cmk.gui.plugins.wato import (
    RulespecGroupCheckParametersStorage,
    CheckParameterRulespecWithItem,
    rulespec_registry,
)


def _parameter_valuespec_bossock_fibers():
    return Tuple(
        title=_("Number of fibers"),
        elements=[
            Integer(title=_("Warning at"), unit=_("fibers")),
            Integer(title=_("Critical at"), unit=_("fibers")),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="bossock_fibers",
        group=RulespecGroupCheckParametersStorage,
        item_spec=lambda: TextAscii(title=_("Node ID")),
        parameter_valuespec=_parameter_valuespec_bossock_fibers,
        title=lambda: _("Number of Running Bossock Fibers"),
    ))
