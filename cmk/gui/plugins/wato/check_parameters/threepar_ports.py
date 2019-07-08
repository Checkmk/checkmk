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
    RulespecGroupCheckParametersNetworking,
)


@rulespec_registry.register
class RulespecCheckgroupParametersThreeparPorts(CheckParameterRulespecWithItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersNetworking

    @property
    def check_group_name(self):
        return "threepar_ports"

    @property
    def title(self):
        return _("3PAR Ports")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
        return Dictionary(elements=[
            ("1_link", MonitoringState(title=_("Link State: CONFIG_WAIT"), default_value=1)),
            ("2_link", MonitoringState(title=_("Link State: ALPA_WAIT"), default_value=1)),
            ("3_link", MonitoringState(title=_("Link State: LOGIN_WAIT"), default_value=1)),
            ("4_link", MonitoringState(title=_("Link State: READY"), default_value=0)),
            ("5_link", MonitoringState(title=_("Link State: LOSS_SYNC"), default_value=2)),
            ("6_link", MonitoringState(title=_("Link State: ERROR_STATE"), default_value=2)),
            ("7_link", MonitoringState(title=_("Link State: XXX"), default_value=1)),
            ("8_link", MonitoringState(title=_("Link State: NOPARTICIPATE"), default_value=0)),
            ("9_link", MonitoringState(title=_("Link State: COREDUMP"), default_value=1)),
            ("10_link", MonitoringState(title=_("Link State: OFFLINE"), default_value=1)),
            ("11_link", MonitoringState(title=_("Link State: FWDEAD"), default_value=1)),
            ("12_link", MonitoringState(title=_("Link State: IDLE_FOR_RESET"), default_value=1)),
            ("13_link", MonitoringState(title=_("Link State: DHCP_IN_PROGESS"), default_value=1)),
            ("14_link", MonitoringState(title=_("Link State: PENDING_RESET"), default_value=1)),
            ("1_fail", MonitoringState(title=_("Failover State: NONE"), default_value=0)),
            ("2_fail", MonitoringState(title=_("Failover State: FAILOVER_PENDING"),
                                       default_value=2)),
            ("3_fail", MonitoringState(title=_("Failover State: FAILED_OVER"), default_value=2)),
            ("4_fail", MonitoringState(title=_("Failover State: ACTIVE"), default_value=2)),
            ("5_fail", MonitoringState(title=_("Failover State: ACTIVE_DOWN"), default_value=2)),
            ("6_fail", MonitoringState(title=_("Failover State: ACTIVE_FAILED"), default_value=2)),
            ("7_fail", MonitoringState(title=_("Failover State: FAILBACK_PENDING"),
                                       default_value=1)),
        ],)

    @property
    def item_spec(self):
        return TextAscii(title=_("Port"), help=_("The Port Description"))
