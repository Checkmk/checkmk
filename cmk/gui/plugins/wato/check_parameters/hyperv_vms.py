#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (Dictionary, MonitoringState, TextAscii)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)

VM_STATES = sorted([
    "Other", "Running", "Off", "Stopping", "Saved", "Paused", "Starting", "Reset", "Saving",
    "Pausing", "Resuming", "FastSaved", "FastSaving", "RunningCritical", "OffCritical",
    "StoppingCritical", "SavedCritical", "PausedCritical", "StartingCritical", "ResetCritical",
    "SavingCritical", "PausingCritical", "ResumingCritical", "FastSavedCritical",
    "FastSavingCritical"
])


def _item_spec_hyperv_vms():
    return TextAscii(
        title=_("Name of the VM"),
        help=_("Specify the name of the VM, for example z4065012."),
        allow_empty=False,
    )


def _parameter_valuespec_hyperv_vms():

    return Dictionary(
        title=_("Map VM state to monitoring state"),
        elements=[(vm_state,
                   MonitoringState(title=_("Monitoring state if VM state is %s" % vm_state),
                                   help=_("Check result if reported VM state is %s" % vm_state),
                                   default_value=0)) for vm_state in VM_STATES],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="hyperv_vms",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_hyperv_vms,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_hyperv_vms,
        title=lambda: _("State of Microsoft Hyper-V Server VMs"),
    ))
