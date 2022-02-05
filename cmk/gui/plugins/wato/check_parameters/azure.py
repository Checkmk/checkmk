#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Optional
from typing import Tuple as TupleType

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import (
    DEF_VALUE,
    Dictionary,
    DropdownChoice,
    Float,
    Integer,
    MonitoringState,
    TextInput,
    Tuple,
)


def _item_spec_azure_agent_info():
    return TextInput(title=_("Azure Agent Info"))


def _parameter_valuespec_azure_agent_info():
    return Dictionary(
        elements=[
            (
                "resource_pinning",
                DropdownChoice(
                    title=_("Resource pinning: Ensure monitored resources are unchanged"),
                    help=_(
                        "If this option is selected, the resources being monitored are stored during"
                        " discovery. The service will go to a warning state, if they change."
                    ),
                    choices=[
                        (True, _("Warn if resources appear or vanish")),
                        (False, _("Silently ignore new or missing resources")),
                    ],
                ),
            ),
            (
                "warning_levels",
                Tuple(
                    title=_("Upper levels for encountered warnings"),
                    elements=[
                        Integer(title=_("Warning at"), default_value=1),
                        Integer(title=_("Critical at"), default_value=10),
                    ],
                ),
            ),
            (
                "exception_levels",
                Tuple(
                    title=_("Upper levels for encountered exceptions"),
                    elements=[
                        Integer(title=_("Warning at"), default_value=1),
                        Integer(title=_("Critical at"), default_value=1),
                    ],
                ),
            ),
            (
                "remaining_reads_levels_lower",
                Tuple(
                    title=_("Lower levels for remaining API reads"),
                    elements=[
                        Integer(title=_("Warning below"), default_value=6000),
                        Integer(title=_("Critical below"), default_value=3000),
                    ],
                ),
            ),
            (
                "remaining_reads_unknown_state",
                MonitoringState(
                    title=_("State if remaining API reads are unknown"),
                    default_value=1,
                ),
            ),
        ],
        ignored_keys=["discovered_resources"],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="azure_agent_info",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_azure_agent_info,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_azure_agent_info,
        title=lambda: _("Azure Agent Info"),
    )
)


def _item_spec_webserver():
    return TextInput(title=_("Name of the service"))


def _parameter_valuespec_webserver():
    return Dictionary(
        elements=[
            (
                "avg_response_time_levels",
                Tuple(
                    title=_("Upper levels for average response time"),
                    elements=[
                        Float(title=_("Warning at"), default_value=1.00, unit="s"),
                        Float(title=_("Critical at"), default_value=10.0, unit="s"),
                    ],
                ),
            ),
            (
                "error_rate_levels",
                Tuple(
                    title=_("Upper levels for rate of server errors"),
                    elements=[
                        Float(title=_("Warning at"), default_value=0.01, unit="1/s"),
                        Float(title=_("Critical at"), default_value=0.04, unit="1/s"),
                    ],
                ),
            ),
            (
                "cpu_time_percent_levels",
                Tuple(
                    title=_("Upper levels for CPU time"),
                    elements=[
                        Float(title=_("Warning at"), default_value=85.0, unit="%"),
                        Float(title=_("Critical at"), default_value=95.0, unit="%"),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="webserver",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_webserver,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_webserver,
        title=lambda: _("Azure web servers (IIS)"),
    )
)


def _item_spec_azure_storageaccounts():
    return TextInput(
        title=_("Storage account name"),
        help=_("Specify storage account names that the rule should apply to"),
    )


def _parameter_valuespec_azure_storageaccounts():
    return Dictionary(
        elements=[
            (
                "ingress_levels",
                Tuple(
                    title=_("Levels on ingress data in bytes"),
                    elements=[
                        Float(title=_("Warning at"), unit="B"),
                        Float(title=_("Critical at"), unit="B"),
                    ],
                ),
            ),
            (
                "egress_levels",
                Tuple(
                    title=_("Levels on egress data in bytes"),
                    elements=[
                        Float(title=_("Warning at"), unit="B"),
                        Float(title=_("Critical at"), unit="B"),
                    ],
                ),
            ),
            (
                "used_capacity_levels",
                Tuple(
                    title=_("Levels on used capacity in bytes"),
                    elements=[
                        Float(title=_("Warning at"), unit="B"),
                        Float(title=_("Critical at"), unit="B"),
                    ],
                ),
            ),
            (
                "server_latency_levels",
                Tuple(
                    title=_("Levels on server latency in seconds"),
                    help=_("Average latency used by Azure Storage to process a successful request"),
                    elements=[
                        Float(title=_("Warning at"), unit="s"),
                        Float(title=_("Critical at"), unit="s"),
                    ],
                ),
            ),
            (
                "e2e_latency_levels",
                Tuple(
                    title=_("Levels on end-to-end latency in seconds"),
                    help=_(
                        "Average end-to-end latency of successful requests made to a storage service"
                    ),
                    elements=[
                        Float(title=_("Warning at"), unit="s"),
                        Float(title=_("Critical at"), unit="s"),
                    ],
                ),
            ),
            (
                "transactions_levels",
                Tuple(
                    title=_("Levels on transaction count"),
                    elements=[
                        Integer(title=_("Warning at")),
                        Integer(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "availability_levels",
                Tuple(
                    title=_("Levels on availability in percent"),
                    elements=[
                        Float(title=_("Warning at"), unit="%"),
                        Float(title=_("Critical at"), unit="%"),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="azure_storageaccounts",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_azure_storageaccounts,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_azure_storageaccounts,
        title=lambda: _("Azure Storage"),
    )
)


def _item_spec_azure_databases():
    return TextInput(
        title=_("Database Name"),
        help=_("Specify database names that the rule should apply to"),
    )


def _parameter_valuespec_azure_databases():
    return Dictionary(
        title=_("Set Levels"),
        elements=[
            (
                "storage_percent_levels",
                Tuple(
                    title=_("Used storage in percent"),
                    elements=[
                        Float(title=_("Warning at"), unit=_("%"), default_value=85.0),
                        Float(title=_("Critical at"), unit=_("%"), default_value=95.0),
                    ],
                ),
            ),
            (
                "cpu_percent_levels",
                Tuple(
                    title=_("CPU in percent"),
                    elements=[
                        Float(title=_("Warning at"), unit=_("%"), default_value=85.0),
                        Float(title=_("Critical at"), unit=_("%"), default_value=95.0),
                    ],
                ),
            ),
            (
                "dtu_percent_levels",
                Tuple(
                    title=_("Database throughput units in percent"),
                    elements=[
                        Float(title=_("Warning at"), unit=_("%"), default_value=40.0),
                        Float(title=_("Critical at"), unit=_("%"), default_value=50.0),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="azure_databases",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_azure_databases,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_azure_databases,
        title=lambda: _("Azure Databases"),
    )
)


def _item_spec_azure_vms():
    return TextInput(title=_("VM name"))


def _parameter_valuespec_azure_vms():
    return Dictionary(
        help=_(
            "To obtain the data required for this check, please configure"
            ' the datasource program "Microsoft Azure".'
        ),
        elements=[
            (
                "map_provisioning_states",
                Dictionary(
                    title=_("Map provisioning states"),
                    elements=[
                        ("succeeded", MonitoringState(title="succeeded")),
                        ("failed", MonitoringState(title="failed", default_value=2)),
                    ],
                ),
            ),
            (
                "map_power_states",
                Dictionary(
                    title=_("Map power states"),
                    elements=[
                        ("starting", MonitoringState(title="starting")),
                        ("running", MonitoringState(title="running")),
                        ("stopping", MonitoringState(title="stopping", default_value=1)),
                        ("stopped", MonitoringState(title="stopped", default_value=1)),
                        ("deallocating", MonitoringState(title="deallocating")),
                        ("deallocated", MonitoringState(title="deallocated")),
                        ("unknown", MonitoringState(title=_("unknown"), default_value=3)),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="azure_vms",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_azure_vms,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_azure_vms,
        title=lambda: _("Azure Virtual Machines"),
    )
)


def _azure_vms_summary_levels(
    title: str,
    lower: Optional[TupleType[int, int]] = None,
    upper: Optional[TupleType[int, int]] = None,
) -> Dictionary:
    return Dictionary(
        title=title,
        elements=[
            (
                "levels_lower",
                Tuple(
                    title=_("Lower levels"),
                    elements=[
                        Integer(
                            title=_("Warning below"),
                            default_value=lower[0] if lower is not None else DEF_VALUE,
                        ),
                        Integer(
                            title=_("Critical below"),
                            default_value=lower[1] if lower is not None else DEF_VALUE,
                        ),
                    ],
                ),
            ),
            (
                "levels",
                Tuple(
                    title=_("Upper levels"),
                    elements=[
                        Integer(
                            title=_("Warning at"),
                            default_value=upper[0] if upper is not None else DEF_VALUE,
                        ),
                        Integer(
                            title=_("Critical at"),
                            default_value=upper[1] if upper is not None else DEF_VALUE,
                        ),
                    ],
                ),
            ),
        ],
    )


def _parameter_valuespec_azure_vms_summary() -> Dictionary:
    return Dictionary(
        help=_(
            "To obtain the data required for this check, please configure"
            ' the datasource program "Microsoft Azure".'
        ),
        elements=[
            (
                "levels_provisioning",
                Dictionary(
                    title=_("Levels for provisioning count"),
                    elements=[
                        (
                            "succeeded",
                            _azure_vms_summary_levels(_("Succeeded provionings"), (0, -1)),
                        ),
                        (
                            "failed",
                            _azure_vms_summary_levels(
                                _("Failed provisionings"),
                                (-1, -1),
                                (1, 1),
                            ),
                        ),
                    ],
                ),
            ),
            (
                "levels_power",
                Dictionary(
                    title=_("Levels for power state count"),
                    elements=[
                        ("starting", _azure_vms_summary_levels(_("Starting VMs"))),
                        ("running", _azure_vms_summary_levels(_("Running VMs"))),
                        ("stopping", _azure_vms_summary_levels(_("Stopping VMs"))),
                        ("stopped", _azure_vms_summary_levels(_("Stopped VMs"))),
                        ("deallocating", _azure_vms_summary_levels(_("Deallocating VMs"))),
                        ("deallocated", _azure_vms_summary_levels(_("Deallocated VMs"))),
                        (
                            "unknown",
                            _azure_vms_summary_levels(_("VMs in unknown state"), upper=(1, 1)),
                        ),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="azure_vms_summary",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_azure_vms_summary,
        title=lambda: _("Azure Virtual Machines Summary"),
    )
)


def _item_spec_azure_virtualnetworkgateways():
    return TextInput(
        title=_("Virtual network gateway name"),
        help=_("Specify virtual network gateway names that the rule should apply to"),
    )


def _parameter_valuespec_azure_virtualnetworkgateways():
    return Dictionary(
        elements=[
            (
                "connections_levels_upper",
                Tuple(
                    title=_("Upper levels on number of Point-to-site connections"),
                    elements=[
                        Float(title=_("Warning at")),
                        Float(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "connections_levels_lower",
                Tuple(
                    title=_("Lower levels on number of Point-to-site connections"),
                    elements=[
                        Float(title=_("Warning below")),
                        Float(title=_("Critical below")),
                    ],
                ),
            ),
            (
                "p2s_bandwidth_levels_upper",
                Tuple(
                    title=_("Upper levels on Point-to-site bandwidth in bytes per second"),
                    elements=[
                        Float(title=_("Warning at"), unit="B/s"),
                        Float(title=_("Critical at"), unit="B/s"),
                    ],
                ),
            ),
            (
                "p2s_bandwidth_levels_lower",
                Tuple(
                    title=_("Lower levels on Point-to-site bandwidth in bytes per second"),
                    elements=[
                        Float(title=_("Warning below"), unit="B/s"),
                        Float(title=_("Critical below"), unit="B/s"),
                    ],
                ),
            ),
            (
                "s2s_bandwidth_levels_upper",
                Tuple(
                    title=_("Upper levels on Site-to-site bandwidth in bytes per second"),
                    elements=[
                        Float(title=_("Warning at"), unit="B/s"),
                        Float(title=_("Critical at"), unit="B/s"),
                    ],
                ),
            ),
            (
                "s2s_bandwidth_levels_lower",
                Tuple(
                    title=_("Lower levels on Site-to-site bandwidth in bytes per second"),
                    elements=[
                        Float(title=_("Warning below"), unit="B/s"),
                        Float(title=_("Critical below"), unit="B/s"),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="azure_virtualnetworkgateways",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_azure_virtualnetworkgateways,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_azure_virtualnetworkgateways,
        title=lambda: _("Azure VNet Gateway"),
    )
)


def _parameter_valuespec_azure_usagedetails():
    return Dictionary(
        help=_(
            "To obtain the data required for this check, please configure"
            ' the datasource program "Microsoft Azure".'
        ),
        elements=[
            (
                "levels",
                Tuple(
                    title=_("Upper levels on daily costs"),
                    help=_(
                        "The levels on costs will be considered to be in the currency"
                        " corresponding to the reported data."
                    ),
                    elements=[
                        Float(title=_("Warning at")),
                        Float(title=_("Critical at")),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="azure_usagedetails",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(title=_("Service Type")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_azure_usagedetails,
        title=lambda: _("Azure Usage Details (Costs)"),
    )
)
