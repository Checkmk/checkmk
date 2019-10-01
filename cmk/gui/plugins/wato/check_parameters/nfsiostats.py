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
    Float,
    Percentage,
    TextAscii,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)


def _parameter_valuespec_nfsiostats():
    return Dictionary(
        title=_("NFS IO Statistics"),
        optional_keys=True,
        elements=[
            ("op_s",
             Tuple(
                 title=_("Operations"),
                 elements=[
                     Float(title=_("Warning at"), default_value=None, unit="1/s"),
                     Float(title=_("Critical at"), default_value=None, unit="1/s"),
                 ],
             )),
            ("rpc_backlog",
             Tuple(
                 title=_("RPC Backlog"),
                 elements=[
                     Float(title=_("Warning below"), default_value=None, unit="queue"),
                     Float(title=_("Critical below"), default_value=None, unit="queue"),
                 ],
             )),
            ("read_ops",
             Tuple(
                 title=_("Read Operations /s"),
                 elements=[
                     Float(title=_("Warning at"), default_value=None, unit="1/s"),
                     Float(title=_("Critical at"), default_value=None, unit="1/s"),
                 ],
             )),
            ("read_b_s",
             Tuple(
                 title=_("Reads size /s"),
                 elements=[
                     Float(title=_("Warning at"), default_value=None, unit="bytes/s"),
                     Float(title=_("Critical at"), default_value=None, unit="bytes/s"),
                 ],
             )),
            ("read_b_op",
             Tuple(
                 title=_("Read bytes per operation"),
                 elements=[
                     Float(title=_("Warning at"), default_value=None, unit="bytes/op"),
                     Float(title=_("Critical at"), default_value=None, unit="bytes/op"),
                 ],
             )),
            ("read_retrans",
             Tuple(
                 title=_("Read Retransmissions"),
                 elements=[
                     Percentage(title=_("Warning at"), default_value=None),
                     Percentage(title=_("Critical at"), default_value=None),
                 ],
             )),
            ("read_avg_rtt_ms",
             Tuple(
                 title=_("Read Average RTT (ms)"),
                 elements=[
                     Float(title=_("Warning at"), default_value=None, unit="ms"),
                     Float(title=_("Critical at"), default_value=None, unit="ms"),
                 ],
             )),
            ("read_avg_exe_ms",
             Tuple(
                 title=_("Read Average Executions (ms)"),
                 elements=[
                     Float(title=_("Warning at"), default_value=None, unit="ms"),
                     Float(title=_("Critical at"), default_value=None, unit="ms"),
                 ],
             )),
            ("write_ops_s",
             Tuple(
                 title=_("Write Operations/s"),
                 elements=[
                     Float(title=_("Warning at"), default_value=None, unit="1/s"),
                     Float(title=_("Critical at"), default_value=None, unit="1/s"),
                 ],
             )),
            ("write_b_s",
             Tuple(
                 title=_("Write size /s"),
                 elements=[
                     Float(title=_("Warning at"), default_value=None, unit="bytes/s"),
                     Float(title=_("Critical at"), default_value=None, unit="bytes/s"),
                 ],
             )),
            ("write_b_op",
             Tuple(
                 title=_("Write bytes per operation"),
                 elements=[
                     Float(title=_("Warning at"), default_value=None, unit="bytes/s"),
                     Float(title=_("Critical at"), default_value=None, unit="bytes/s"),
                 ],
             )),
            ("write_retrans",
             Tuple(
                 title=_("Write Retransmissions"),
                 elements=[
                     Percentage(title=_("Warning at"), default_value=None),
                     Percentage(title=_("Critical at"), default_value=None),
                 ],
             )),
            ("write_avg_rtt_ms",
             Tuple(
                 title=_("Write Avg RTT (ms)"),
                 elements=[
                     Float(title=_("Warning at"), default_value=None, unit="ms"),
                     Float(title=_("Critical at"), default_value=None, unit="ms"),
                 ],
             )),
            ("write_avg_exe_ms",
             Tuple(
                 title=_("Write Avg exe (ms)"),
                 elements=[
                     Float(title=_("Warning at"), default_value=None, unit="ms"),
                     Float(title=_("Critical at"), default_value=None, unit="ms"),
                 ],
             )),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="nfsiostats",
        group=RulespecGroupCheckParametersStorage,
        item_spec=lambda: TextAscii(title=_("NFS IO Statistics"),),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_nfsiostats,
        title=lambda: _("NFS IO Statistics"),
    ))
