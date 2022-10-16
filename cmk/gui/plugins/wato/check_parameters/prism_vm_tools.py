#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersVirtualization,
)
from cmk.gui.valuespec import Dictionary, DropdownChoice


def _parameter_valuespec_prism_vm_tools():
    return Dictionary(
        elements=[
            (
                "tools_install",
                DropdownChoice(
                    title=_("Tools install state"),
                    choices=[
                        ("installed", _("installed")),
                        ("not_installed", _("not installed")),
                    ],
                    default_value="installed",
                ),
            ),
            (
                "tools_enabled",
                DropdownChoice(
                    title=_("VMTools activation state"),
                    choices=[
                        ("enabled", _("enabled")),
                        ("disabled", _("disabled")),
                    ],
                    default_value="enabled",
                ),
            ),
        ],
        title=_("Wanted VM State for defined Nutanix VMs"),
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="prism_vm_tools",
        group=RulespecGroupCheckParametersVirtualization,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_prism_vm_tools,
        title=lambda: _("Nutanix Prism VM Tools"),
    )
)
