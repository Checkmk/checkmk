#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Alternative, Dictionary, FixedValue, MonitoringState, TextInput

# these default values were suggested by Aldi Sued
VM_STATES_DEFVALS = [
    ("FastSaved", 0),
    ("FastSavedCritical", 2),
    ("FastSaving", 0),
    ("FastSavingCritical", 2),
    ("Off", 1),
    ("OffCritical", 2),
    ("Other", 3),
    ("Paused", 0),
    ("PausedCritical", 2),
    ("Pausing", 0),
    ("PausingCritical", 2),
    ("Reset", 1),
    ("ResetCritical", 2),
    ("Resuming", 0),
    ("ResumingCritical", 2),
    ("Running", 0),
    ("RunningCritical", 2),
    ("Saved", 0),
    ("SavedCritical", 2),
    ("Saving", 0),
    ("SavingCritical", 2),
    ("Starting", 0),
    ("StartingCritical", 2),
    ("Stopping", 1),
    ("StoppingCritical", 2),
]


def _item_spec_hyperv_vms():
    return TextInput(
        title=_("Name of the VM"),
        help=_("Specify the name of the VM, for example z4065012."),
        allow_empty=False,
    )


def _parameter_valuespec_hyperv_vms() -> Alternative:
    return Alternative(
        title=_("Translation of VM state to monitoring state"),
        elements=[
            Dictionary(
                title=_("Direct mapping of VM state to monitoring state"),
                help=_(
                    "Define a direct translation of the possible states of the VM to monitoring "
                    "states, i.e. to the result of the check. This overwrites the default "
                    "mapping used by the check."
                ),
                elements=[
                    (
                        vm_state,
                        MonitoringState(
                            title=_("Monitoring state if VM state is %s") % vm_state,
                            default_value=default_value,
                        ),
                    )
                    for vm_state, default_value in VM_STATES_DEFVALS
                ],
            ),
            FixedValue(
                value={"compare_discovery": True},
                title=_("Compare against discovered state"),
                totext=_("Compare the current state of the VM against the discovered state"),
                help=_(
                    "Compare the current state of the VM against the state at the point in time "
                    "when the VM was discovered. If the two states do not match, the service "
                    "will go to CRIT. Note that this only works if the check is not executed as "
                    "a manual check. If you choose this option for manual checks, the service "
                    "will go always to UNKN."
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="hyperv_vms",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_hyperv_vms,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_hyperv_vms,
        title=lambda: _("Microsoft Hyper-V Server VM state"),
    )
)
