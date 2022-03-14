#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, Optional, TextInput


def _parameter_valuespec_proxmox_ve_vm_info():
    # use Dictionary as Optional returning an empty dict if empty
    return Dictionary(
        title=_("Check Parameter"),
        elements=[
            (
                "required_vm_status",
                Optional(
                    title=_("Modify: Check VM Status (off: keep default)"),
                    label=_("Activate Check (off: ignore VM status)"),
                    default_value=True,
                    valuespec=TextInput(
                        title=_("Warn if VM status value is not"),
                        default_value="running",
                    ),
                ),
            )
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        title=lambda: _("Proxmox VE VM Info"),
        check_group_name="proxmox_ve_vm_info",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_proxmox_ve_vm_info,
    )
)
