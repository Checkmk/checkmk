#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Dictionary,
    MonitoringState,
    TextAscii,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


def _parameter_valuespec_mssql_instance():
    return Dictionary(elements=[("map_connection_state",
                                 MonitoringState(title=_("Connection status"), default_value=2))],)


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="mssql_instance",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextAscii(title=_("Instance identifier"),),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_mssql_instance,
        title=lambda: _("MSSQL Instance"),
    ))
