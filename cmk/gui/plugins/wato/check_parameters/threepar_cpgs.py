#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.check_parameters.utils import vs_filesystem
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)
from cmk.gui.valuespec import TextInput

rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="threepar_cpgs",
        group=RulespecGroupCheckParametersStorage,
        item_spec=lambda: TextInput(title=_("CPG member name"), allow_empty=False),
        match_type="dict",
        parameter_valuespec=vs_filesystem,
        title=lambda: _("3PAR CPG (used space and growth)"),
    )
)
