#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    Levels,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.plugins.wato.utils.simple_levels import SimpleLevels
from cmk.gui.valuespec import (
    CascadingDropdown,
    Dictionary,
    Migrate,
    Percentage,
    TextInput,
    ValueSpec,
)

# A notes about the names of the Dictionary elements. They correspond to the names of the metrics in
# the check plug-in. Please do not change them.


def _vs_disk_elements() -> Sequence[tuple[str, ValueSpec]]:
    return [
        (
            "disk_utilization",
            Levels(title=_("Disk usage"), unit="%", default_value=(80, 90)),
        ),
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
            (
                "util",
                SimpleLevels(Percentage, title=_("CPU utilization"), default_value=(80, 90)),
            ),
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


def _vs_latency_disk() -> ValueSpec:
    return Dictionary(
        title=_("Levels disk"),
        elements=[
            *_vs_disk_elements(),
            (
                "disk_average_read_wait",
                Levels(title=_("Average disk read latency"), unit="s"),
            ),
            (
                "disk_average_write_wait",
                Levels(title=_("Average disk write latency"), unit="s"),
            ),
            ("latency", Levels(title=_("Average disk latency"), unit="s")),
        ],
    )


def _item_spec_filestore() -> ValueSpec:
    return TextInput(title=_("Server"))


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="gcp_filestore_disk",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_vs_latency_disk,
        title=lambda: _("GCP/Filestore"),
        item_spec=_item_spec_filestore,
    )
)


def migrate_predictive_cost(value: dict[str, object]) -> dict[str, object]:
    if isinstance(value.get("levels"), dict):
        return {"levels": None}
    return value


def _vs_cost() -> ValueSpec:
    return Migrate(
        Dictionary(
            title=_("Levels monthly GCP costs"),
            elements=[
                (
                    "levels",
                    SimpleLevels(title=_("Amount in billed currency")),
                ),
            ],
        ),
        migrate=migrate_predictive_cost,
    )


def _item_spec_cost() -> ValueSpec:
    return TextInput(title=_("Project"))


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="gcp_cost",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_vs_cost,
        title=lambda: _("GCP Cost"),
        item_spec=_item_spec_cost,
    )
)
