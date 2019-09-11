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
    Checkbox,
    Dictionary,
    Integer,
    TextAscii,
    Transform,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersDiscovery,
    RulespecGroupCheckParametersStorage,
    HostRulespec,
)


def _valuespec_inventory_heartbeat_crm_rules():
    return Dictionary(
        title=_("Heartbeat CRM Discovery"),
        elements=[
            ("naildown_dc",
             Checkbox(
                 title=_("Naildown the DC"),
                 label=_("Mark the currently distinguished controller as preferred one"),
                 help=_(
                     "Nails down the DC to the node which is the DC during discovery. The check "
                     "will report CRITICAL when another node becomes the DC during later checks."))
            ),
            ("naildown_resources",
             Checkbox(
                 title=_("Naildown the resources"),
                 label=_("Mark the nodes of the resources as preferred one"),
                 help=_(
                     "Nails down the resources to the node which is holding them during discovery. "
                     "The check will report CRITICAL when another holds the resource during later checks."
                 ))),
        ],
        help=_('This rule can be used to control the discovery for Heartbeat CRM checks.'),
        optional_keys=[],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupCheckParametersDiscovery,
        match_type="dict",
        name="inventory_heartbeat_crm_rules",
        valuespec=_valuespec_inventory_heartbeat_crm_rules,
    ))


def _heartbeat_crm_transform_heartbeat_crm(params):
    if isinstance(params, dict):
        return params
    par_dict = {'max_age': params[0]}
    if params[1]:
        par_dict['dc'] = params[1]
    if params[2] > -1:
        par_dict['num_nodes'] = params[2]
    if params[3] > -1:
        par_dict['num_resources'] = params[3]
    return par_dict


def _parameter_valuespec_heartbeat_crm():
    return Transform(Dictionary(
        elements=[
            ("max_age",
             Integer(
                 title=_("Maximum age"),
                 help=_("Maximum accepted age of the reported data in seconds"),
                 unit=_("seconds"),
                 default_value=60,
             )),
            ("dc",
             TextAscii(
                 allow_empty=False,
                 title=_("Expected DC"),
                 help=_("The hostname of the expected distinguished controller of the cluster"),
             )),
            ("num_nodes",
             Integer(
                 min_value=0,
                 default_value=2,
                 title=_("Number of Nodes"),
                 help=_("The expected number of nodes in the cluster"),
             )),
            ("num_resources",
             Integer(
                 min_value=0,
                 title=_("Number of Resources"),
                 help=_("The expected number of resources in the cluster"),
             )),
        ],
        optional_keys=["dc", "num_nodes", "num_resources"],
    ),
                     forth=_heartbeat_crm_transform_heartbeat_crm)


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="heartbeat_crm",
        group=RulespecGroupCheckParametersStorage,
        parameter_valuespec=_parameter_valuespec_heartbeat_crm,
        title=lambda: _("Heartbeat CRM general status"),
    ))
