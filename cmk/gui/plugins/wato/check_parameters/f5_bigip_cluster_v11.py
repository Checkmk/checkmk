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
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersNetworking,
)


def _parameter_valuespec_f5_bigip_cluster_v11():
    return Dictionary(
        title=_("Interpretation of Config Sync Status"),
        elements=[
            ("0", MonitoringState(title="Unknown", default_value=3)),
            ("1", MonitoringState(title="Syncing", default_value=0)),
            ("2", MonitoringState(title="Need Manual Sync", default_value=1)),
            ("3", MonitoringState(title="In Sync", default_value=0)),
            ("4", MonitoringState(title="Sync Failed", default_value=2)),
            ("5", MonitoringState(title="Sync Disconnected", default_value=2)),
            ("6", MonitoringState(title="Standalone", default_value=2)),
            ("7", MonitoringState(title="Awaiting Initial Sync", default_value=1)),
            ("8", MonitoringState(title="Incompatible Version", default_value=2)),
            ("9", MonitoringState(title="Partial Sync", default_value=2)),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="f5_bigip_cluster_v11",
        group=RulespecGroupCheckParametersNetworking,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_f5_bigip_cluster_v11,
        title=lambda: _("Configuration Sync Status for F5 BigIP devices"),
    ))
