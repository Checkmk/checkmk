#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.check_parameters.gcp import (
    _vs_cpu,
    _vs_disk_elements,
    _vs_network_elements,
)
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    Levels,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.plugins.wato.utils.simple_levels import SimpleLevels
from cmk.gui.valuespec import Dictionary, MonitoringState, Percentage, TextInput, ValueSpec

# A notes about the names of the Dictionary elements. They correspond to the names of the metrics in
# the check plug-in. Please do not change them.


def _vs_sql_status() -> ValueSpec:
    return Dictionary(
        title=_("Map GCP status to check mk"),
        elements=[
            ("RUNNING", MonitoringState(title=_("Running"), default_value=0)),
            ("SUSPEND", MonitoringState(title=_("Suspend"), default_value=1)),
            ("RUNNABLE", MonitoringState(title=_("Runnable"), default_value=0)),
            ("PENDING_CREATE", MonitoringState(title=_("Pending create"), default_value=3)),
            ("MAINTENANCE", MonitoringState(title=_("Maintenance"), default_value=3)),
            ("FAILED", MonitoringState(title=_("Failed"), default_value=2)),
            ("UNKNOWN_STATE", MonitoringState(title=_("Unknown"), default_value=3)),
        ],
    )


def _item_spec_sql() -> ValueSpec:
    return TextInput(title=_("Database server"))


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="gcp_sql_status",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_vs_sql_status,
        title=lambda: _("GCP/Cloud SQL status"),
        item_spec=_item_spec_sql,
    )
)


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="gcp_sql_cpu",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_vs_cpu,
        title=lambda: _("GCP/Cloud SQL CPU utilization"),
        item_spec=_item_spec_sql,
    )
)


def _vs_sql_memory() -> ValueSpec:
    return Dictionary(
        title=_("Levels memory"),
        elements=[
            (
                "memory_util",
                SimpleLevels(Percentage, title=_("Memory utilization"), default_value=(80, 90)),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="gcp_sql_memory",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_vs_sql_memory,
        title=lambda: _("GCP/Cloud SQL memory utilization"),
        item_spec=_item_spec_sql,
    )
)


def _vs_sql_network() -> ValueSpec:
    return Dictionary(
        title=_("Levels on network traffic"),
        elements=[
            *_vs_network_elements(),
            ("connections", SimpleLevels(title=_("Active connections"))),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="gcp_sql_network",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_vs_sql_network,
        title=lambda: _("GCP/Cloud SQL network"),
        item_spec=_item_spec_sql,
    )
)


def _vs_disk() -> ValueSpec:
    return Dictionary(title=_("Levels disk"), elements=_vs_disk_elements())


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="gcp_sql_disk",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_vs_disk,
        title=lambda: _("GCP/Cloud SQL disk"),
        item_spec=_item_spec_sql,
    )
)


def _vs_sql_replication_lag() -> ValueSpec:
    return Dictionary(
        title=_("Parameters for the replication lag"),
        elements=[
            (
                "replication_lag",
                Levels(title=_("Upper levels on the replication lag"), unit="second"),
            )
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="gcp_replication_lag",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_vs_sql_replication_lag,
        title=lambda: _("GCP/Cloud SQL replication lag"),
        item_spec=_item_spec_sql,
    )
)
