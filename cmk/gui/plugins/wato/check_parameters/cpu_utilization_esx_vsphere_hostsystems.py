#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.check_parameters.cpu_utilization import cpu_util_elements
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersOperatingSystem,
)
from cmk.gui.valuespec import Dictionary, Integer, ListOf, Tuple


def _vsphere_esx_hostsystem_cluster_elements():
    return [
        (
            "cluster",
            ListOf(
                valuespec=Tuple(
                    orientation="horizontal",
                    elements=[
                        Integer(
                            title=_("Nodes"),
                            help=_(
                                "Apply these levels to clusters that have at least the following number of nodes:"
                            ),
                            minvalue=1,
                        ),
                        Dictionary(elements=cpu_util_elements()),
                    ],
                ),
                title=_("Clusters: node specific CPU utilization"),
                help=_(
                    "Configure thresholds that apply to clusters based on how many nodes "
                    "they have."
                ),
            ),
        ),
    ]


def _parameter_valuespec_cpu_utilization_esx_vsphere_hostsystem():
    return Dictionary(
        help=_(
            "This rule configures levels for the CPU utilization (not load) for "
            "VMWare ESX host systems. "
            "The utilization percentage is computed with respect to the total "
            "number of CPUs. "
        ),
        elements=cpu_util_elements() + _vsphere_esx_hostsystem_cluster_elements(),
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="cpu_utilization_esx_vsphere_hostsystem",
        group=RulespecGroupCheckParametersOperatingSystem,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_cpu_utilization_esx_vsphere_hostsystem,
        title=lambda: _("ESX Vsphere host system CPU utilization"),
    )
)
