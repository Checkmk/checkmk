#!/usr/bin/env python
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import Levels
from cmk.gui.plugins.wato.utils.simple_levels import SimpleLevels
from cmk.gui.valuespec import CascadingDropdown, Dictionary, Percentage, ValueSpec

# A notes about the names of the Dictionary elements. They correspond to the names of the metrics in
# the check plugin. Please do not change them.


def _vs_disk_elements() -> Sequence[tuple[str, ValueSpec]]:
    return [
        ("disk_utilization", Levels(title=_("Disk usage"), unit="%", default_value=(80, 90))),
        ("disk_read_ios", Levels(title=_("Number of read IOPS"))),
        ("disk_write_ios", Levels(title=_("Number of write IOPS"))),
    ]


def _vs_network_elements() -> Sequence[tuple[str, ValueSpec]]:
    return [
        ("net_data_sent", SimpleLevels(title=_("Data sent"), unit="bytes/s")),
        ("net_data_recv", SimpleLevels(title=_("Data received"), unit="bytes/s")),
    ]


def _vs_cpu() -> ValueSpec:
    return Dictionary(
        title=_("Levels CPU"),
        elements=[
            ("util", SimpleLevels(Percentage, title=_("CPU utilization"), default_value=(80, 90))),
        ],
    )


def _vs_percentile_choice(
    dropdown_title: str, choice_title: str, choice_unit: str
) -> CascadingDropdown:
    return CascadingDropdown(
        title=dropdown_title,
        choices=[
            (
                50,
                _("50th percentile"),
                Levels(title=choice_title, unit=choice_unit),
            ),
            (
                95,
                _("95th percentile"),
                Levels(title=choice_title, unit=choice_unit),
            ),
            (
                99,
                _("99th percentile"),
                Levels(title=choice_title, unit=choice_unit),
            ),
        ],
    )
