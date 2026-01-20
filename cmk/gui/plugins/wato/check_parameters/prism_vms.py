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
from cmk.gui.valuespec import Dictionary, DropdownChoice, TextInput


def _parameters_valuespec_prism_vms() -> Dictionary:
    status_choice = [
        ("on", _("On")),
        ("unknown", _("Unknown")),
        ("off", _("Off")),
        ("powering_on", _("Powering on")),
        ("shutting_down", _("Shutting down")),
        ("powering_off", _("Powered Off")),
        ("pausing", _("Pausing")),
        ("paused", _("Paused")),
        ("suspending", _("Suspending")),
        ("suspended", _("Suspended")),
        ("resuming", _("Resuming")),
        ("resetting", _("Resetting")),
        ("migrating", _("Migrating")),
    ]
    return Dictionary(
        elements=[
            (
                "system_state",
                DropdownChoice(
                    title=_("Wanted VM State"),
                    choices=status_choice,
                    default_value="on",
                ),
            ),
        ],
        title=_("Wanted VM State for defined Nutanix VMs"),
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="prism_vms",
        item_spec=lambda: TextInput(title=_("VM")),
        group=RulespecGroupCheckParametersVirtualization,
        match_type="dict",
        parameter_valuespec=_parameters_valuespec_prism_vms,
        title=lambda: _("Nutanix VM State"),
    )
)
