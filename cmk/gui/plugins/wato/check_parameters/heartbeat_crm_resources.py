#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)
from cmk.gui.valuespec import Alternative, Dictionary, FixedValue, MonitoringState, TextInput


def _item_spec_heartbeat_crm_resources():
    return TextInput(
        title=_("Resource Name"),
        help=_("The name of the cluster resource as shown in the service name."),
        allow_empty=False,
    )


def _parameter_valuespec_heartbeat_crm_resources() -> Dictionary:
    return Dictionary(
        elements=[
            (
                "expected_node",
                Alternative(
                    title=_("Expected node"),
                    help=_("The host name of the expected node to hold this resource."),
                    elements=[
                        FixedValue(value=None, totext="", title=_("Do not check the node")),
                        TextInput(allow_empty=False, title=_("Expected node")),
                    ],
                ),
            ),
            (
                "monitoring_state_if_unmanaged_nodes",
                MonitoringState(
                    title=_("State if at least one node is unmanaged"),
                    default_value=1,
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="heartbeat_crm_resources",
        group=RulespecGroupCheckParametersStorage,
        item_spec=_item_spec_heartbeat_crm_resources,
        parameter_valuespec=_parameter_valuespec_heartbeat_crm_resources,
        title=lambda: _("Heartbeat CRM resource status"),
    )
)
