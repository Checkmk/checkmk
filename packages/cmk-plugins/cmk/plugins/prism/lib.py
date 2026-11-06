#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"
# mypy: disable-error-code="no-any-return"

import json
from collections.abc import Iterable, Sequence
from typing import Any

from cmk.agent_based.v2 import StringTable
from cmk.plugins.prism.v4_models import DiskStats, newest, Samples

PrismAPIData = dict[str, Any]


def _legacy_tier(tier: str | None) -> str | None:
    """The legacy API knows only these two tiers, others count toward neither"""
    if tier is None:
        return None
    if tier.startswith("SSD"):
        return "ssd"
    return "das-sata" if tier == "DAS_SATA" else None


def sum_newest(samples: Iterable[Samples]) -> int:
    return sum(value for series in samples if (value := newest(series)) is not None)


def tier_usage_stats(disks: Sequence[tuple[str | None, DiskStats]]) -> dict[str, str]:
    """The usage stats of the legacy API per storage tier, from the tier and stats of each disk"""
    usage_stats: dict[str, str] = {}
    for tier in ("ssd", "das-sata"):
        stats = [disk_stats for disk_tier, disk_stats in disks if _legacy_tier(disk_tier) == tier]
        usage_stats[f"storage_tier.{tier}.capacity_bytes"] = str(
            sum_newest(disk_stats.disk_capacity_bytes for disk_stats in stats)
        )
        usage_stats[f"storage_tier.{tier}.free_bytes"] = str(
            sum_newest(disk_stats.disk_free_bytes for disk_stats in stats)
        )
    return usage_stats


def v4_power_state(power_state: str) -> str:
    """The v4 power state as the legacy API reports it"""
    return "unknown" if power_state == "UNDETERMINED" else power_state.lower()


PRISM_POWER_STATES = {
    "on": 0,
    "unknown": 3,
    "off": 1,
    "powering_on": 0,
    "shutting_down": 1,
    "powering_off": 1,
    "pausing": 1,
    "paused": 1,
    "suspending": 1,
    "suspended": 1,
    "resuming": 0,
    "resetting": 1,
    "migrating": 0,
}


def load_json(string_table: StringTable) -> PrismAPIData:
    try:
        return json.loads(string_table[0][0])
    except IndexError, json.decoder.JSONDecodeError:
        return {}
