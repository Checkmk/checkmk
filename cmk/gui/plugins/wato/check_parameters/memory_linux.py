#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal, Union

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.check_parameters.memory_arbor import (  # PredictiveMemoryChoice, # not yet implemented
    DualMemoryLevels,
    FreePercentage,
    FreeSize,
    UsedPercentage,
    UsedSize,
)
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersOperatingSystem,
)
from cmk.gui.valuespec import CascadingDropdown, DEF_VALUE, Dictionary, Sentinel, Transform


def UpperMemoryLevels(
    what,
    default_percents=None,
    of_what=None,
    default_levels_type: Union[Literal["ignore", "abs_used", "perc_used"], Sentinel] = DEF_VALUE,
):
    return CascadingDropdown(
        title=_("Upper levels for %s") % what,
        choices=[
            (
                "perc_used",
                _("Percentual levels%s") % (of_what and (_(" in relation to %s") % of_what) or ""),
                UsedPercentage(default_percents, of_what),
            ),
            ("abs_used", _("Absolute levels"), UsedSize()),
            # PredictiveMemoryChoice(what), # not yet implemented
            ("ignore", _("Do not impose levels")),
        ],
        default_value=default_levels_type,
    )


def LowerMemoryLevels(what, default_percents=None, of_what=None, help_text=None):
    return CascadingDropdown(
        title=_("Lower levels for %s") % what,
        help=help_text,
        choices=[
            ("perc_free", _("Percentual levels"), FreePercentage(default_percents, of_what)),
            ("abs_free", _("Absolute levels"), FreeSize()),
            # PredictiveMemoryChoice(what), # not yet implemented
            ("ignore", _("Do not impose levels")),
        ],
    )


def transform_memory_levels(p):
    if "handle_hw_corrupted_error" in p:
        del p["handle_hw_corrupted_error"]
        p["levels_hardwarecorrupted"] = ("abs_used", (1, 1))
    return p


def _parameter_valuespec_memory_linux():
    return Transform(
        valuespec=Dictionary(
            elements=[
                ("levels_ram", DualMemoryLevels(_("RAM"))),
                ("levels_swap", DualMemoryLevels(_("Swap"))),
                ("levels_virtual", DualMemoryLevels(_("Total virtual memory"), (80.0, 90.0))),
                (
                    "levels_total",
                    UpperMemoryLevels(_("Total Data in relation to RAM"), (120.0, 150.0), _("RAM")),
                ),
                ("levels_shm", UpperMemoryLevels(_("Shared memory"), (20.0, 30.0), _("RAM"))),
                ("levels_pagetables", UpperMemoryLevels(_("Page tables"), (8.0, 16.0), _("RAM"))),
                ("levels_writeback", UpperMemoryLevels(_("Disk Writeback"))),
                (
                    "levels_committed",
                    UpperMemoryLevels(_("Committed memory"), (100.0, 150.0), _("RAM + Swap")),
                ),
                (
                    "levels_commitlimit",
                    LowerMemoryLevels(_("Commit Limit"), (20.0, 10.0), _("RAM + Swap")),
                ),
                (
                    "levels_available",
                    LowerMemoryLevels(
                        _("Estimated RAM for new processes"),
                        (20.0, 10.0),
                        _("RAM"),
                        _(
                            "If the host has a kernel of version 3.14 or newer, the information MemAvailable is provided: "
                            '"An estimate of how much memory is available for starting new '
                            "applications, without swapping. Calculated from MemFree, "
                            "SReclaimable, the size of the file LRU lists, and the low "
                            "watermarks in each zone. "
                            "The estimate takes into account that the system needs some "
                            "page cache to function well, and that not all reclaimable "
                            "slab will be reclaimable, due to items being in use. The "
                            'impact of those factors will vary from system to system." '
                            "(https://www.kernel.org/doc/Documentation/filesystems/proc.txt)"
                        ),
                    ),
                ),
                ("levels_vmalloc", LowerMemoryLevels(_("Largest Free VMalloc Chunk"))),
                (
                    "levels_hardwarecorrupted",
                    UpperMemoryLevels(_("Hardware Corrupted"), (1, 1), _("RAM")),
                ),
            ],
        ),
        forth=transform_memory_levels,
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="memory_linux",
        group=RulespecGroupCheckParametersOperatingSystem,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_memory_linux,
        title=lambda: _("Memory and Swap usage on Linux"),
    )
)
