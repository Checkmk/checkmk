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
    MonitoringState,
    TextAscii,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)


def _item_spec_ibm_svc_mdisk():
    return TextAscii(
        title=_("IBM SVC disk"),
        help=_("Name of the disk, e.g. mdisk0"),
    )


def _parameter_valuespec_ibm_svc_mdisk():
    return Dictionary(
        optional_keys=False,
        elements=[
            (
                "online_state",
                MonitoringState(
                    title=_("Resulting state if disk is online"),
                    default_value=0,
                ),
            ),
            (
                "degraded_state",
                MonitoringState(
                    title=_("Resulting state if disk is degraded"),
                    default_value=1,
                ),
            ),
            (
                "offline_state",
                MonitoringState(
                    title=_("Resulting state if disk is offline"),
                    default_value=2,
                ),
            ),
            (
                "excluded_state",
                MonitoringState(
                    title=_("Resulting state if disk is excluded"),
                    default_value=2,
                ),
            ),
            (
                "managed_mode",
                MonitoringState(
                    title=_("Resulting state if disk is in managed mode"),
                    default_value=0,
                ),
            ),
            (
                "array_mode",
                MonitoringState(
                    title=_("Resulting state if disk is in array mode"),
                    default_value=0,
                ),
            ),
            (
                "image_mode",
                MonitoringState(
                    title=_("Resulting state if disk is in image mode"),
                    default_value=0,
                ),
            ),
            (
                "unmanaged_mode",
                MonitoringState(
                    title=_("Resulting state if disk is in unmanaged mode"),
                    default_value=1,
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="ibm_svc_mdisk",
        group=RulespecGroupCheckParametersStorage,
        item_spec=_item_spec_ibm_svc_mdisk,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_ibm_svc_mdisk,
        title=lambda: _("IBM SVC Disk"),
    ))
