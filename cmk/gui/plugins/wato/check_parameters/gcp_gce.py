#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.plugins.wato.utils.simple_levels import SimpleLevels
from cmk.gui.valuespec import Dictionary, Filesize, Integer, Percentage, TextInput, ValueSpec

# A notes about the names of the Dictionary elements. They correspond to the names of the metrics in
# the check plug-in. Please do not change them.


def _vs_gce_cpu() -> Dictionary:
    return Dictionary(
        title=_("Levels CPU"),
        elements=[
            ("util", SimpleLevels(Percentage, title=_("CPU utilization"))),
            ("vcores", SimpleLevels(Integer, title=_("Number of vCPUs reserved for the VM"))),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="gcp_gce_cpu",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_vs_gce_cpu,
        title=lambda: _("GCP/GCE CPU utilization"),
    )
)


def _vs_gce_disk() -> Dictionary:
    return Dictionary(
        title=_("Levels disk IO"),
        elements=[
            (
                "disk_read_throughput",
                SimpleLevels(Filesize, title=_("Disk read throughput per second")),
            ),
            (
                "disk_write_throughput",
                SimpleLevels(Filesize, title=_("Disk write throughput per second")),
            ),
            ("disk_read_ios", SimpleLevels(Integer, title=_("Disk read operations"), unit="ops")),
            ("disk_write_ios", SimpleLevels(Integer, title=_("Disk write operations"), unit="ops")),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="gcp_gce_disk",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_vs_gce_disk,
        title=lambda: _("GCP/GCE disk IO"),
    )
)


def _item_spec_gce_storage() -> ValueSpec:
    return TextInput(title=_("Device"))


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="gcp_gce_storage",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_vs_gce_disk,
        title=lambda: _("GCP/GCE storage IO"),
        item_spec=_item_spec_gce_storage,
    )
)
