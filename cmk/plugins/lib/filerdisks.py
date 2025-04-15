#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from cmk.agent_based.v2 import check_levels, CheckResult, Metric, render, Result, State


@dataclass(frozen=True, kw_only=True)
class FilerDisk:
    state: str
    identifier: str
    type: str = ""
    capacity: int = 0


FILER_DISKS_CHECK_DEFAULT_PARAMETERS = {
    "failed_spare_ratio": (1.0, 50.0),
    "offline_spare_ratio": (1.0, 50.0),
}


def _check_total_capacity(disks: Sequence[FilerDisk]) -> CheckResult:
    total_capacity = sum(disk.capacity for disk in disks)

    if not total_capacity:
        return

    yield Result(state=State.OK, summary=f"Total raw capacity: {render.disksize(total_capacity)}")
    yield Metric("disk_capacity", total_capacity)


def _check_spare_disks(spare_disks: int, spare_disk_levels: Any) -> CheckResult:
    yield from check_levels(
        value=int(spare_disks),
        levels_lower=(
            ("fixed", (float(spare_disk_levels[0]), float(spare_disk_levels[1])))
            if spare_disk_levels
            else ("no_levels", None)
        ),
        label="Spare disks",
        metric_name="spare_disks",
        render_func=lambda x: f"{int(x)}",
    )


def _check_parity_disks(disks: Sequence[FilerDisk]) -> CheckResult:
    parity_disks = [disk for disk in disks if disk.type == "parity"]
    prefailed_parity = [disk for disk in parity_disks if disk.state == "prefailed"]
    if len(parity_disks) > 0:
        yield Result(
            state=State.OK,
            summary=f"Parity disks: {len(parity_disks)} ({len(prefailed_parity)} prefailed)",
        )

    for name, disk_type in [("Data", "data"), ("Parity", "parity")]:
        total_disks = [disk for disk in disks if disk.type == disk_type]
        prefailed_disks = [disk for disk in total_disks if disk.state == "prefailed"]
        if len(total_disks) > 0:
            info_text = "%s disks" % len(total_disks)
            if len(prefailed_disks) > 0:
                info_text += " (%d prefailed)" % (prefailed_disks)  # type: ignore[str-format]
            yield Result(state=State.OK, summary=info_text)

            info_texts = []
            for disk in prefailed_disks:
                info_texts.append(disk.identifier)
            if len(info_texts) > 0:
                yield Result(
                    state=State.OK, summary=f"{name} Disk Details: {' / '.join(info_texts)}"
                )


def _check_failed_offline_disks(
    state: Mapping[str, list], params: Mapping[str, Any]
) -> CheckResult:
    for disk_state in ["failed", "offline"]:
        info_texts = []
        for disk in state[disk_state]:
            info_texts.append(disk.identifier)
        if len(info_texts) > 0:
            yield Result(
                state=State.OK,
                summary="{} Disk Details: {}".format(disk_state, " / ".join(info_texts)),
            )

            warn, crit = params["%s_spare_ratio" % disk_state]
            ratio = (
                float(len(state[disk_state])) / (len(state[disk_state]) + len(state["spare"])) * 100
            )
            return_state = None
            if ratio >= crit:
                return_state = State.CRIT
            elif ratio >= warn:
                return_state = State.WARN
            if return_state is not None:
                yield Result(
                    state=return_state,
                    summary=f"Too many {disk_state} disks (warn/crit at {warn:.1f}%/{crit:.1f}%)",
                )


def check_filer_disks(disks: Sequence[FilerDisk], params: Mapping[str, Any]) -> CheckResult:
    """
    We consider prefailed disk unavailable.
    In the code here, this assumption has been made for 9 years without any problem ever being raised.
    """

    yield from _check_total_capacity(disks)

    state: dict = {
        "prefailed": [],
        "failed": [],
        "offline": [],
        "spare": [],
    }

    for disk in disks:
        for what, disks_in_state in state.items():
            if disk.state == what:
                disks_in_state.append(disk)

    unavail_disks = len(state["prefailed"] + state["failed"] + state["offline"])
    yield Result(state=State.OK, summary=f"Total disks: {len(disks) - unavail_disks}")
    yield Metric("disks", len(disks))

    yield from _check_spare_disks(len(state["spare"]), params.get("number_of_spare_disks"))

    yield Result(state=State.OK, summary=f"Failed disks: {unavail_disks}")
    yield Metric(name="failed_disks", value=unavail_disks)

    yield from _check_parity_disks(disks)

    yield from _check_failed_offline_disks(state, params)
