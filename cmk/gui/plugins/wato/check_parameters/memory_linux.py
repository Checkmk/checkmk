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
    CascadingDropdown,
    Dictionary,
    Transform,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersOperatingSystem,
)
from cmk.gui.plugins.wato.check_parameters.memory_arbor import (
    DualMemoryLevels,
    FreePercentage,
    UsedPercentage,
    FreeSize,
    UsedSize,
    # PredictiveMemoryChoice, # not yet implemented
)


def UpperMemoryLevels(what, default_percents=None, of_what=None):
    return CascadingDropdown(
        title=_("Upper levels for %s") % what,
        choices=[
            ("perc_used", _("Percentual levels%s") % (of_what and
                                                      (_(" in relation to %s") % of_what) or ""),
             UsedPercentage(default_percents, of_what)),
            ("abs_used", _("Absolute levels"), UsedSize()),
            # PredictiveMemoryChoice(what), # not yet implemented
            ("ignore", _("Do not impose levels")),
        ])


def LowerMemoryLevels(what, default_percents=None, of_what=None, help_text=None):
    return CascadingDropdown(
        title=_("Lower levels for %s") % what,
        help=help_text,
        choices=[
            ("perc_free", _("Percentual levels"), FreePercentage(default_percents, of_what)),
            ("abs_free", _("Absolute levels"), FreeSize()),
            # PredictiveMemoryChoice(what), # not yet implemented
            ("ignore", _("Do not impose levels")),
        ])


def transform_memory_levels(p):
    if "handle_hw_corrupted_error" in p:
        del p["handle_hw_corrupted_error"]
        p['levels_hardwarecorrupted'] = ('abs_used', (1, 1))
    return p


@rulespec_registry.register
class RulespecCheckgroupParametersMemoryLinux(CheckParameterRulespecWithoutItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersOperatingSystem

    @property
    def check_group_name(self):
        return "memory_linux"

    @property
    def title(self):
        return _("Memory and Swap usage on Linux")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
        return Transform(
            Dictionary(elements=[
                ("levels_ram", DualMemoryLevels(_("RAM"))),
                ("levels_swap", DualMemoryLevels(_("Swap"))),
                ("levels_virtual", DualMemoryLevels(_("Total virtual memory"), (80.0, 90.0))),
                ("levels_total",
                 UpperMemoryLevels(_("Total Data in relation to RAM"), (120.0, 150.0), _("RAM"))),
                ("levels_shm", UpperMemoryLevels(_("Shared memory"), (20.0, 30.0), _("RAM"))),
                ("levels_pagetables", UpperMemoryLevels(_("Page tables"), (8.0, 16.0), _("RAM"))),
                ("levels_writeback", UpperMemoryLevels(_("Disk Writeback"))),
                ("levels_committed",
                 UpperMemoryLevels(_("Committed memory"), (100.0, 150.0), _("RAM + Swap"))),
                ("levels_commitlimit",
                 LowerMemoryLevels(_("Commit Limit"), (20.0, 10.0), _("RAM + Swap"))),
                ("levels_available",
                 LowerMemoryLevels(
                     _("Estimated RAM for new processes"), (20.0, 10.0), _("RAM"),
                     _("If the host has a kernel of version 3.14 or newer, the information MemAvailable is provided: "
                       "\"An estimate of how much memory is available for starting new "
                       "applications, without swapping. Calculated from MemFree, "
                       "SReclaimable, the size of the file LRU lists, and the low "
                       "watermarks in each zone. "
                       "The estimate takes into account that the system needs some "
                       "page cache to function well, and that not all reclaimable "
                       "slab will be reclaimable, due to items being in use. The "
                       "impact of those factors will vary from system to system.\" "
                       "(https://www.kernel.org/doc/Documentation/filesystems/proc.txt)"))),
                ("levels_vmalloc", LowerMemoryLevels(_("Largest Free VMalloc Chunk"))),
                ("levels_hardwarecorrupted",
                 UpperMemoryLevels(_("Hardware Corrupted"), (1, 1), _("RAM"))),
            ],),
            forth=transform_memory_levels,
        )
