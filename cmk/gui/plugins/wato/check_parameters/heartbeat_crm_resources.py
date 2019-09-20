#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Optional,
    TextAscii,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)


def _item_spec_heartbeat_crm_resources():
    return TextAscii(
        title=_("Resource Name"),
        help=_("The name of the cluster resource as shown in the service description."),
        allow_empty=False,
    )


def _parameter_valuespec_heartbeat_crm_resources():
    return Optional(
        TextAscii(allow_empty=False),
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
    ))
