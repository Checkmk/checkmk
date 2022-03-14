#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)
from cmk.gui.valuespec import Optional, TextInput


def _item_spec_heartbeat_crm_resources():
    return TextInput(
        title=_("Resource Name"),
        help=_("The name of the cluster resource as shown in the service description."),
        allow_empty=False,
    )


def _parameter_valuespec_heartbeat_crm_resources():
    return Optional(
        valuespec=TextInput(allow_empty=False),
        title=_("Expected node"),
        help=_("The hostname of the expected node to hold this resource."),
        none_label=_("Do not enforce the resource to be hold by a specific node."),
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
