#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Shared GUI↔daemon perf_data label/unit parsing for Checkmk Maps.

Both the daemon (``cmk.maps.backend``, to build rrddata column specs) and the
GUI (``cmk.maps.gui``, for the perfdata source picker) split a raw Nagios
``perf_data`` string into its metric labels — and both must handle quoted
labels that contain spaces (``'disk usage'=50GB``). Neither component may
import the other (module-layer boundary), so this parser lives here in
``cmk.maps.shared`` — the same seam as ``cmk.maps.shared.states``.

The caller picks what it needs off each entry: the daemon uses ``label`` +
``unit``, the GUI only ``label``. This replaces a buggy daemon variant that
``.split()`` on whitespace and so tore quoted labels apart.
"""

import re
from typing import Final, TypedDict


class PerfMetric(TypedDict):
    """One parsed perf_data entry: metric label and its unit suffix."""

    label: str
    unit: str


# One perf_data token: an optionally single-quoted label, ``=``, then the value
# part up to the next whitespace. The label ``=`` is captured as its own group so
# a quoted label may itself contain ``=`` (``'a=b'=5``) — splitting on the first
# ``=`` would otherwise tear the label at the wrong place. The unquoted label
# stops at ``=``/whitespace (a bare Nagios label carries neither).
_PERF_TOKEN_RE: Final = re.compile(r"(?:'(?P<qlabel>[^']+)'|(?P<label>[^\s=]+))=(?P<value>\S*)")
# Leading numeric value, then the trailing unit letters (``5ms`` -> ``ms``).
_UNIT_RE: Final = re.compile(r"[-\d.]+([a-zA-Z%]*)")


def parse_perf_metrics(perf_data: str) -> list[PerfMetric]:
    """Parse a perf_data string into ``[{label, unit}]``, quoted labels intact."""
    results: list[PerfMetric] = []
    for match in _PERF_TOKEN_RE.finditer(perf_data):
        qlabel = match.group("qlabel")
        label = qlabel if qlabel is not None else match.group("label")
        unit = _UNIT_RE.match(match.group("value").split(";")[0])
        results.append({"label": label, "unit": unit.group(1) if unit else ""})
    return results
