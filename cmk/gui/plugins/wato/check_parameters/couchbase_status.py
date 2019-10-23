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
    MonitoringState,
    TextAscii,
    Dictionary,
)
from cmk.gui.plugins.wato import (
    RulespecGroupCheckParametersApplications,
    CheckParameterRulespecWithItem,
    rulespec_registry,
)


def _parameter_valuespec_couchbase_status():
    return Dictionary(
        title=_('Couchbase Node: Cluster status'),
        elements=[
            ('warmup_state',
             MonitoringState(
                 title=_('Resulting state if the status is "warmup"'),
                 default_value=0,
             )),
            ('unhealthy_state',
             MonitoringState(
                 title=_('Resulting state if the status is "unhealthy"'),
                 default_value=2,
             )),
            (
                'inactive_added_state',
                MonitoringState(
                    title=_('Resulting state if the cluster membership status is "inactiveAdded"'),
                    default_value=1,
                ),
            ),
            (
                'inactive_failed_state',
                MonitoringState(
                    title=_('Resulting state if the cluster membership status is "inactiveFailed"'),
                    default_value=2,
                ),
            ),
        ])


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="couchbase_status",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        item_spec=lambda: TextAscii(title=_('Node name')),
        parameter_valuespec=_parameter_valuespec_couchbase_status,
        title=lambda: _("Couchbase Status"),
    ))
