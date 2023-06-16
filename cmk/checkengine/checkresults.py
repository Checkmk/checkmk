#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import dataclasses
from collections.abc import Sequence

from cmk.utils.check_utils import worst_service_state
from cmk.utils.hostaddress import HostName
from cmk.utils.type_defs import MetricName

__all__ = ["ActiveCheckResult", "MetricTuple", "ServiceCheckResult", "state_markers"]


# Symbolic representations of states in plugin output
# TODO(ml): Should probably be of type enum::int -> str
state_markers = ("", "(!)", "(!!)", "(?)")


MetricTuple = tuple[
    MetricName,
    float,
    float | None,
    float | None,
    float | None,
    float | None,
]


@dataclasses.dataclass
class ServiceCheckResult:
    state: int = 0
    output: str = ""
    metrics: Sequence[MetricTuple] = ()

    @classmethod
    def item_not_found(cls) -> ServiceCheckResult:
        return cls(3, "Item not found in monitoring data")

    @classmethod
    def received_no_data(cls) -> ServiceCheckResult:
        return cls(3, "Check plugin received no monitoring data")

    @classmethod
    def check_not_implemented(cls) -> ServiceCheckResult:
        return cls(3, "Check plugin not implemented")

    @classmethod
    def cluster_received_no_data(cls, nodes: Sequence[HostName]) -> ServiceCheckResult:
        node_hint = f"configured nodes: {', '.join(nodes)}" if nodes else "no nodes configured"
        return cls(3, f"Clustered service received no monitoring data ({node_hint})")


@dataclasses.dataclass
class ActiveCheckResult:
    state: int = 0
    summary: str = ""
    details: tuple[str, ...] | list[str] = ()  # Sequence, but not str...
    metrics: tuple[str, ...] | list[str] = ()

    def as_text(self) -> str:
        return "\n".join(
            (
                " | ".join((self.summary, " ".join(self.metrics)))
                if self.metrics
                else self.summary,
                "".join(f"{line}\n" for line in self.details),
            )
        ).strip()

    @classmethod
    def from_subresults(cls, *subresults: ActiveCheckResult) -> ActiveCheckResult:
        return cls(
            state=worst_service_state(*(s.state for s in subresults), default=0),
            summary=", ".join(cls._add_marker(s.summary, s.state) for s in subresults if s.summary),
            details=tuple(
                detail
                for s in subresults
                for detail in [
                    *s.details[:-1],
                    *(cls._add_marker(d, s.state) for d in s.details[-1:]),
                ]
            ),
            metrics=tuple(m for s in subresults for m in s.metrics),
        )

    @staticmethod
    def _add_marker(txt: str, state: int) -> str:
        marker = state_markers[state]
        return txt if txt.endswith(marker) else f"{txt}{marker}"
