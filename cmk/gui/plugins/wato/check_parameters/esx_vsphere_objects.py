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
from cmk.gui.valuespec import Dictionary, MonitoringState, TextInput


def _item_spec_esx_vsphere_objects():
    return TextInput(
        title=_("Name of the VM/HostSystem"),
        help=_(
            "Please do not forget to specify either <tt>VM</tt> or <tt>HostSystem</tt>. Example: <tt>VM abcsrv123</tt>. Also note, "
            "that we match the <i>beginning</i> of the name."
        ),
        regex="(^VM|HostSystem)( .*|$)",
        regex_error=_("The name of the system must begin with <tt>VM</tt> or <tt>HostSystem</tt>."),
        allow_empty=False,
    )


def _parameter_valuespec_esx_vsphere_objects():
    return Dictionary(
        help=_(
            "Usually the check goes to WARN if a VM or host is powered off and OK otherwise. "
            "You can change this behaviour on a per-state-basis here."
        ),
        optional_keys=False,
        elements=[
            (
                "states",
                Dictionary(
                    title=_("Target states"),
                    optional_keys=False,
                    elements=[
                        (
                            "poweredOn",
                            MonitoringState(
                                title=_("Powered ON"),
                                help=_("Check result if the host or VM is powered on"),
                                default_value=0,
                            ),
                        ),
                        (
                            "poweredOff",
                            MonitoringState(
                                title=_("Powered OFF"),
                                help=_("Check result if the host or VM is powered off"),
                                default_value=1,
                            ),
                        ),
                        (
                            "suspended",
                            MonitoringState(
                                title=_("Suspended"),
                                help=_("Check result if the host or VM is suspended"),
                                default_value=1,
                            ),
                        ),
                        (
                            "unknown",
                            MonitoringState(
                                title=_("Unknown"),
                                help=_(
                                    "Check result if the host or VM state is reported as <i>unknown</i>"
                                ),
                                default_value=3,
                            ),
                        ),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="esx_vsphere_objects",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_esx_vsphere_objects,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_esx_vsphere_objects,
        title=lambda: _("ESX host and virtual machine states"),
    )
)
