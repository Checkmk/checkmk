#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.check_parameters.fortigate_sessions import fortigate_sessions_element
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersNetworking,
)
from cmk.gui.valuespec import TextInput

rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="fortigate_node_sessions",
        group=RulespecGroupCheckParametersNetworking,
        item_spec=lambda: TextInput(title=_("Node name"), allow_empty=False),
        parameter_valuespec=fortigate_sessions_element,
        title=lambda: _("Fortigate Cluster Active Sessions"),
    )
)
