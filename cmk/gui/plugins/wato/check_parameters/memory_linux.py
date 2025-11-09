#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

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
from cmk.gui.valuespec import CascadingDropdown, DEF_VALUE, Dictionary, Sentinel


def UpperMemoryLevels(
    what: str,
    default_percents: tuple[float, float] | None = None,
    of_what: str | None = None,
    default_levels_type: Literal["ignore", "abs_used", "perc_used"] | Sentinel = DEF_VALUE,
) -> CascadingDropdown:
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


def LowerMemoryLevels(
    what: str,
    default_percents: tuple[float, float] | None = None,
    of_what: str | None = None,
    help_text: str | None = None,
) -> CascadingDropdown:
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


def _parameter_valuespec_memory_linux() -> Dictionary:
    return Dictionary(
        elements=[
            ("levels_ram", DualMemoryLevels(_("RAM"))),
            ("levels_swap", DualMemoryLevels(_("Swap"))),
            ("levels_virtual", DualMemoryLevels(_("Total virtual memory"), (80.0, 90.0))),
            (
                "levels_total",
                UpperMemoryLevels(_("Total data in relation to RAM"), (120.0, 150.0), _("RAM")),
            ),
            ("levels_shm", UpperMemoryLevels(_("Shared memory"), (20.0, 30.0), _("RAM"))),
            ("levels_pagetables", UpperMemoryLevels(_("Page tables"), (8.0, 16.0), _("RAM"))),
            ("levels_writeback", UpperMemoryLevels(_("Disk writeback"))),
            (
                "levels_committed",
                UpperMemoryLevels(_("Committed memory"), (100.0, 150.0), _("RAM + Swap")),
            ),
            (
                "levels_commitlimit",
                LowerMemoryLevels(_("Commit limit"), (20.0, 10.0), _("RAM + Swap")),
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
            ("levels_vmalloc", LowerMemoryLevels(_("Largest free VMalloc chunk"))),
            (
                "levels_hardwarecorrupted",
                UpperMemoryLevels(_("Hardware corrupted"), (1, 1), _("RAM")),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="memory_linux",
        group=RulespecGroupCheckParametersOperatingSystem,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_memory_linux,
        title=lambda: _("Memory and swap usage on Linux"),
    )
)
