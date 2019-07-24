#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2018             mk@mathias-kettner.de |
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
    RulespecGroupCheckParametersNetworking,
    register_check_parameters,
    Levels,
)

register_check_parameters(
    RulespecGroupCheckParametersNetworking, "checkpoint_packets",
    _("Checkpoint Firewall Packet Rates"),
    Dictionary(elements=[
        ("accepted",
         Levels(title=_("Maximum Rate of Accepted Packets"),
                default_value=None,
                default_levels=(100000, 200000),
                unit="pkts/sec")),
        ("rejected",
         Levels(title=_("Maximum Rate of Rejected Packets"),
                default_value=None,
                default_levels=(100000, 200000),
                unit="pkts/sec")),
        ("dropped",
         Levels(title=_("Maximum Rate of Dropped Packets"),
                default_value=None,
                default_levels=(100000, 200000),
                unit="pkts/sec")),
        ("logged",
         Levels(title=_("Maximum Rate of Logged Packets"),
                default_value=None,
                default_levels=(100000, 200000),
                unit="pkts/sec")),
        ("espencrypted",
         Levels(title=_("Maximum Rate of ESP Encrypted Packets"),
                default_value=None,
                default_levels=(100000, 200000),
                unit="pkts/sec")),
        ("espdecrypted",
         Levels(title=_("Maximum Rate of ESP Decrypted Packets"),
                default_value=None,
                default_levels=(100000, 200000),
                unit="pkts/sec")),
    ]), None, "dict")

register_check_parameters(
    RulespecGroupCheckParametersNetworking,
    "checkpoint_tunnels",
    _("Checkpoint Tunnel Status"),
    Dictionary(elements=[
        ("Active", MonitoringState(
            title=_("State when VPN status is Active"),
            default_value=0,
        )),
        ("Destroy", MonitoringState(
            title=_("State when VPN status is Destroy"),
            default_value=1,
        )),
        ("Idle", MonitoringState(
            title=_("State when VPN status is Idle"),
            default_value=0,
        )),
        ("Phase1", MonitoringState(
            title=_("State when VPN status is Phase1"),
            default_value=2,
        )),
        ("Down", MonitoringState(
            title=_("State when VPN status is Down"),
            default_value=2,
        )),
        ("Init", MonitoringState(
            title=_("State when VPN status is Init"),
            default_value=1,
        )),
    ]),
    TextAscii(
        title=_("Name of VPN tunnel"),
        allow_empty=True,
    ),
    match_type="dict",
)
