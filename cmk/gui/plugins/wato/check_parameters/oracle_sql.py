#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, MonitoringState, TextInput


def _parameter_valuespec_oracle_sql() -> Dictionary:
    return Dictionary(
        elements=[
            ("instance_error_state", MonitoringState(title=_("Instance error state"))),
            ("perfdata_error_state", MonitoringState(title=_("Perfdata error state"))),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="oracle_sql",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(title=_("Custom SQL")),
        parameter_valuespec=_parameter_valuespec_oracle_sql,
        title=lambda: _("Oracle Custom SQLs"),
    )
)
