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
    Dictionary,
    Percentage,
    TextAscii,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)
from cmk.gui.plugins.wato.check_parameters.utils import filesystem_elements


def _item_spec_esx_vsphere_datastores():
    return TextAscii(title=_("Datastore Name"),
                     help=_("The name of the Datastore"),
                     allow_empty=False)


def _parameter_valuespec_esx_vsphere_datastores():
    return Dictionary(
        elements=filesystem_elements + [
            ("provisioning_levels",
             Tuple(
                 title=_("Provisioning Levels"),
                 help=
                 _("A provisioning of more than 100% is called "
                   "over provisioning and can be a useful strategy for saving disk space. But you cannot guarantee "
                   "any longer that every VM can really use all space that it was assigned. Here you can "
                   "set levels for the maximum provisioning. A warning level of 150% will warn at 50% over provisioning."
                  ),
                 elements=[
                     Percentage(title=_("Warning at a provisioning of"),
                                maxvalue=None,
                                default_value=120.0),
                     Percentage(title=_("Critical at a provisioning of"),
                                maxvalue=None,
                                default_value=150.0),
                 ],
             )),
        ],
        hidden_keys=["flex_levels"],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="esx_vsphere_datastores",
        group=RulespecGroupCheckParametersStorage,
        item_spec=_item_spec_esx_vsphere_datastores,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_esx_vsphere_datastores,
        title=lambda: _("ESX Datastores (used space and growth)"),
    ))
