#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Collects what each measurement found and prints it as one table at the end of the run.

A comparison is only useful side by side. Logging each figure as it is measured scatters them
through the output and leaves the reader to do the arithmetic; and log lines are at the mercy
of whatever log level the GUI happens to configure while it loads. So the numbers are gathered
here and rendered once, through pytest's terminal summary, which always reaches the reader.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field


@dataclass(frozen=True, kw_only=True)
class Measurement:
    """One page, measured once, at one shape."""

    scenario: str
    page: str
    #: ``load`` for a first page load, ``refresh`` for what the page's timer repeats.
    phase: str
    sites: int
    hosts_per_site: int
    queries: int
    #: Round trips to *every* site. This is the figure a WAN link multiplies.
    fan_outs: float
    rows: int
    payload_bytes: int
    queries_by_kind: Mapping[str, int]
    seconds: float | None = None
    #: CPU seconds the measured site's own processes spent, and the resident memory they held.
    #: Only a run against a real site can know these; in-process runs leave them unset.
    cpu_seconds: float | None = None
    rss_mib: float | None = None


@dataclass
class Report:
    measurements: list[Measurement] = field(default_factory=list)

    def add(self, measurement: Measurement) -> None:
        self.measurements.append(measurement)

    def lines(self) -> Sequence[str]:
        if not self.measurements:
            return ()

        header = (
            f"{'scenario':<26} {'page':<22} {'phase':<8} {'sites':>5} {'hosts/site':>10} "
            f"{'queries':>7} {'fan-outs':>8} {'rows':>8} {'KiB':>9} {'ms':>8} "
            f"{'cpu s':>7} {'MiB':>8}  breakdown"
        )
        rows = [header, "-" * len(header)]
        for m in self.measurements:
            rows.append(
                f"{m.scenario:<26} {m.page:<22} {m.phase:<8} {m.sites:>5} {m.hosts_per_site:>10} "
                f"{m.queries:>7} {m.fan_outs:>8.1f} {m.rows:>8} {m.payload_bytes / 1024:>9.1f} "
                f"{'' if m.seconds is None else f'{m.seconds * 1000:.1f}':>8} "
                f"{'' if m.cpu_seconds is None else f'{m.cpu_seconds:.1f}':>7} "
                f"{'' if m.rss_mib is None else f'{m.rss_mib:.0f}':>8}  "
                f"{_breakdown(m.queries_by_kind)}"
            )
        rows.extend(("", *_ratios(self.measurements)))
        return rows


def _breakdown(queries_by_kind: Mapping[str, int]) -> str:
    return ", ".join(f"{kind}={count}" for kind, count in sorted(queries_by_kind.items()))


def _ratios(measurements: Sequence[Measurement]) -> Sequence[str]:
    """The classic page against the page replacing it, at each shape and phase.

    A ratio above 1 means the new page costs more. That is the whole answer the suite exists to
    give; everything above it is the evidence.
    """
    by_key: dict[tuple[str, str, int, int], dict[str, Measurement]] = {}
    for m in measurements:
        generation = "vue" if m.page.endswith("_vue") else "classic"
        subject = m.page.removesuffix("_vue").removesuffix("_classic")
        by_key.setdefault((subject, m.phase, m.sites, m.hosts_per_site), {})[generation] = m

    lines = ["new page vs classic view (>1 means the new page costs more)"]
    header = (
        f"{'page':<22} {'phase':<8} {'sites':>5} {'hosts/site':>10} "
        f"{'queries':>8} {'rows':>8} {'bytes':>8} {'time':>8}"
    )
    lines.extend((header, "-" * len(header)))
    for (subject, phase, sites, hosts), pair in sorted(by_key.items()):
        if len(pair) != 2:
            continue
        classic, vue = pair["classic"], pair["vue"]
        lines.append(
            f"{subject:<22} {phase:<8} {sites:>5} {hosts:>10} "
            f"{_ratio(vue.queries, classic.queries):>8} "
            f"{_ratio(vue.rows, classic.rows):>8} "
            f"{_ratio(vue.payload_bytes, classic.payload_bytes):>8} "
            f"{_ratio(vue.seconds, classic.seconds):>8}"
        )
    return lines


def _ratio(new: float | None, old: float | None) -> str:
    if new is None or old is None:
        return "-"
    if not old:
        return "n/a"
    return f"{new / old:.2f}x"
