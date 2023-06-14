#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersVirtualization,
)
from cmk.gui.valuespec import Dictionary, DropdownChoice


def _parameter_valuespec_prism_remote_support():
    return Dictionary(
        elements=[
            (
                "tunnel_state",
                DropdownChoice(
                    title=_("Target remote tunnel state"),
                    help=_("Configure the target state of the remote support tunnel."),
                    choices=[
                        (False, "Tunnel should be inactive"),
                        (True, "Tunnel should be active"),
                    ],
                    default_value=False,
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="prism_remote_support",
        group=RulespecGroupCheckParametersVirtualization,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_prism_remote_support,
        title=lambda: _("Nutanix Prism Support State"),
    )
)
