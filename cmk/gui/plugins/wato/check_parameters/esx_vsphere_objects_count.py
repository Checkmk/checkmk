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
from cmk.gui.valuespec import Dictionary, Integer, ListOf, ListOfStrings, MonitoringState


def _parameter_valuespec_esx_vsphere_objects_count():
    return Dictionary(
        optional_keys=False,
        elements=[
            (
                "distribution",
                ListOf(
                    valuespec=Dictionary(
                        optional_keys=False,
                        elements=[
                            ("vm_names", ListOfStrings(title=_("VMs"))),
                            ("hosts_count", Integer(title=_("Number of hosts"), default_value=2)),
                            (
                                "state",
                                MonitoringState(title=_("State if violated"), default_value=1),
                            ),
                        ],
                    ),
                    title=_("VM distribution"),
                    help=_(
                        "You can specify lists of VM names and a number of hosts,"
                        " to make sure the specfied VMs are distributed across at least so many hosts."
                        " E.g. provide two VM names and set 'Number of hosts' to two,"
                        " to make sure those VMs are not running on the same host."
                    ),
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="esx_vsphere_objects_count",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_esx_vsphere_objects_count,
        title=lambda: _("ESX hosts: distribution of virtual machines"),
    )
)
