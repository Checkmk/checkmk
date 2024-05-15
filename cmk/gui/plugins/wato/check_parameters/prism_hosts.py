#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersVirtualization,
)
from cmk.gui.valuespec import Dictionary, TextInput


def _parameters_valuespec_prism_hosts():
    return Dictionary(
        elements=[
            (
                "system_state",
                TextInput(
                    title=_("Wanted Host State"),
                    allow_empty=False,
                    default_value="NORMAL",
                ),
            ),
        ],
        title=_("Wanted Host State for defined Nutanix Host"),
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="prism_hosts",
        item_spec=lambda: TextInput(title=_("Host")),
        group=RulespecGroupCheckParametersVirtualization,
        match_type="dict",
        parameter_valuespec=_parameters_valuespec_prism_hosts,
        title=lambda: _("Nutanix Host State"),
    )
)
