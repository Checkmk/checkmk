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
    Age,
    Dictionary,
    ListChoice,
    TextAscii,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    Levels,
    RulespecGroupCheckParametersStorage,
    ABCHostValueRulespec,
)


@rulespec_registry.register
class RulespecDiskstatInventory(ABCHostValueRulespec):
    @property
    def group(self):
        return RulespecGroupCheckParametersStorage

    @property
    def name(self):
        return "diskstat_inventory"

    @property
    def valuespec(self):
        return ListChoice(
            title=_("Discovery mode for Disk IO check"),
            help=_("This rule controls which and how many checks will be created "
                   "for monitoring individual physical and logical disks. "
                   "Note: the option <i>Create a summary for all read, one for "
                   "write</i> has been removed. Some checks will still support "
                   "this settings, but it will be removed there soon."),
            choices=[
                ("summary", _("Create a summary over all physical disks")),
                # This option is still supported by some checks, but is deprecated and
                # we fade it out...
                # ( "legacy",   _("Create a summary for all read, one for write") ),
                ("physical", _("Create a separate check for each physical disk")),
                ("lvm", _("Create a separate check for each LVM volume (Linux)")),
                ("vxvm", _("Creata a separate check for each VxVM volume (Linux)")),
                ("diskless", _("Creata a separate check for each partition (XEN)")),
            ],
            default_value=['summary'],
        )


@rulespec_registry.register
class RulespecCheckgroupParametersDiskstat(CheckParameterRulespecWithItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersStorage

    @property
    def check_group_name(self):
        return "diskstat"

    @property
    def title(self):
        return _("Levels for disk IO")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
        return Dictionary(
            help=
            _("With this rule you can set limits for various disk IO statistics. "
              "Keep in mind that not all of these settings may be applicable for the actual "
              "check. For example, if the check doesn't provide a <i>Read wait</i> information in its "
              "output, any configuration setting referring to <i>Read wait</i> will have no effect."
             ),
            elements=[
                ("read",
                 Levels(
                     title=_("Read throughput"),
                     unit=_("MB/s"),
                     default_levels=(50.0, 100.0),
                 )),
                ("write",
                 Levels(
                     title=_("Write throughput"),
                     unit=_("MB/s"),
                     default_levels=(50.0, 100.0),
                 )),
                ("utilization",
                 Levels(
                     title=_("Disk Utilization"),
                     unit=_("%"),
                     default_levels=(80.0, 90.0),
                 )),
                ("latency",
                 Levels(
                     title=_("Disk Latency"),
                     unit=_("ms"),
                     default_levels=(80.0, 160.0),
                 )),
                ("read_latency",
                 Levels(
                     title=_("Disk Read Latency"),
                     unit=_("ms"),
                     default_levels=(80.0, 160.0),
                 )),
                ("write_latency",
                 Levels(
                     title=_("Disk Write Latency"),
                     unit=_("ms"),
                     default_levels=(80.0, 160.0),
                 )),
                ("read_wait", Levels(title=_("Read wait"),
                                     unit=_("ms"),
                                     default_levels=(30.0, 50.0))),
                ("write_wait",
                 Levels(title=_("Write wait"), unit=_("ms"), default_levels=(30.0, 50.0))),
                ("average",
                 Age(
                     title=_("Averaging"),
                     help=_(
                         "When averaging is set, then all of the disk's metrics are averaged "
                         "over the selected interval - rather then the check interval. This allows "
                         "you to make your monitoring less reactive to short peaks. But it will also "
                         "introduce a loss of accuracy in your graphs. "),
                     default_value=300,
                 )),
                ("read_ios",
                 Levels(title=_("Read operations"), unit=_("1/s"), default_levels=(400.0, 600.0))),
                ("write_ios",
                 Levels(title=_("Write operations"), unit=_("1/s"), default_levels=(300.0, 400.0))),
            ],
        )

    @property
    def item_spec(self):
        return TextAscii(
            title=_("Device"),
            help=_(
                "For a summarized throughput of all disks, specify <tt>SUMMARY</tt>,  "
                "a per-disk IO is specified by the drive letter, a colon and a slash on Windows "
                "(e.g. <tt>C:/</tt>) or by the device name on Linux/UNIX (e.g. <tt>/dev/sda</tt>).")
        )
