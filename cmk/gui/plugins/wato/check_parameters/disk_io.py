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
    Float,
    Integer,
    TextAscii,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    Levels,
    RulespecGroupCheckParametersStorage,
)


def _item_spec_disk_io():
    return TextAscii(
        title=_("Device"),
        help=_("For a summarized throughput of all disks, specify <tt>SUMMARY</tt>, for a "
               "sum of read or write throughput write <tt>read</tt> or <tt>write</tt> resp. "
               "A per-disk IO is specified by the drive letter, a colon and a slash on Windows "
               "(e.g. <tt>C:/</tt>) or by the device name on Linux/UNIX (e.g. <tt>/dev/sda</tt>)."))


def _parameter_valuespec_disk_io():
    return Dictionary(elements=[
        ("read",
         Levels(title=_("Read throughput"),
                unit=_("MB/s"),
                default_value=None,
                default_levels=(50.0, 100.0))),
        ("write",
         Levels(title=_("Write throughput"),
                unit=_("MB/s"),
                default_value=None,
                default_levels=(50.0, 100.0))),
        ("average",
         Integer(title=_("Average"),
                 help=_("When averaging is set, a floating average value "
                        "of the disk throughput is computed and the levels for read "
                        "and write will be applied to the average instead of the current "
                        "value."),
                 default_value=5,
                 minvalue=1,
                 unit=_("minutes"))),
        ("latency",
         Tuple(
             title=_("IO Latency"),
             elements=[
                 Float(title=_("warning at"), unit=_("ms"), default_value=80.0),
                 Float(title=_("critical at"), unit=_("ms"), default_value=160.0),
             ],
         )),
        (
            "latency_perfdata",
            Checkbox(title=_("Performance Data for Latency"),
                     label=_("Collect performance data for disk latency"),
                     help=_("Note: enabling performance data for the latency might "
                            "cause incompatibilities with existing historical data "
                            "if you are running PNP4Nagios in SINGLE mode.")),
        ),
        ("read_ql",
         Tuple(
             title=_("Read Queue-Length"),
             elements=[
                 Float(title=_("warning at"), default_value=80.0),
                 Float(title=_("critical at"), default_value=90.0),
             ],
         )),
        ("write_ql",
         Tuple(
             title=_("Write Queue-Length"),
             elements=[
                 Float(title=_("warning at"), default_value=80.0),
                 Float(title=_("critical at"), default_value=90.0),
             ],
         )),
        (
            "ql_perfdata",
            Checkbox(title=_("Performance Data for Queue Length"),
                     label=_("Collect performance data for disk latency"),
                     help=_("Note: enabling performance data for the latency might "
                            "cause incompatibilities with existing historical data "
                            "if you are running PNP4Nagios in SINGLE mode.")),
        ),
        ("read_ios",
         Levels(
             title=_("Read operations"),
             unit=_("1/s"),
             default_levels=(400.0, 600.0),
         )),
        ("write_ios",
         Levels(
             title=_("Write operations"),
             unit=_("1/s"),
             default_levels=(300.0, 400.0),
         )),
    ],)


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="disk_io",
        group=RulespecGroupCheckParametersStorage,
        item_spec=_item_spec_disk_io,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_disk_io,
        title=lambda: _("Levels on disk IO (old style checks)"),
    ))
