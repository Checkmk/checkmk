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
    DropdownChoice,
    TextAscii,
    Transform,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)


@rulespec_registry.register
class RulespecCheckgroupParametersRaidDisk(CheckParameterRulespecWithItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersStorage

    @property
    def check_group_name(self):
        return "raid_disk"

    @property
    def title(self):
        return _("RAID: state of a single disk")

    @property
    def parameter_valuespec(self):
        return Transform(
            Dictionary(elements=[
                (
                    "expected_state",
                    TextAscii(
                        title=_("Expected state"),
                        help=_("State the disk is expected to be in. Typical good states "
                               "are online, host spare, OK and the like. The exact way of how "
                               "to specify a state depends on the check and hard type being used. "
                               "Please take examples from discovered checks for reference.")),
                ),
                ("use_device_states",
                 DropdownChoice(
                     title=_("Use device states and overwrite expected status"),
                     choices=[
                         (False, _("Ignore")),
                         (True, _("Use device states")),
                     ],
                     default_value=True,
                 )),
            ],),
            forth=lambda x: isinstance(x, str) and {"expected_state": x} or x,
        )

    @property
    def item_spec(self):
        return TextAscii(title=_("Number or ID of the disk"),
                         help=_("How the disks are named depends on the type of hardware being "
                                "used. Please look at already discovered checks for examples."))
