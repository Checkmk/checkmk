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

The grammar is Maps' own, shared with the SPA's ``perf.ts``: it keeps the labels
as Livestatus reports them, which ``cmk.graphing_engine`` renames, and quotes
labels with single quotes only.
"""

import re
from typing import Final, TypedDict


class PerfMetric(TypedDict):
    """One parsed perf_data entry: metric label and its unit suffix."""

    label: str
    unit: str


# The core does not bound perfdata; longer entries resolve to nothing.
MAX_PERF_DATA_LENGTH: Final = 65536

# A token is a quoted label (which may hold spaces and "=") with its value, or
# a whitespace-free part. Each alternative stops at the next quote or
# whitespace, so a long input is read once. Mirrors parsePerfData in
# cmk-frontend-vue/src/maps/utils/perf.ts.
_PERF_TOKEN_RE: Final = re.compile(r"'[^']*'=\S*|\S+")
_VALUE_RE: Final = re.compile(r"-?(?:\d+(?:\.\d*)?|\.\d+)([a-zA-Z%/]*)")


def _label_and_value(token: str) -> tuple[str, str] | None:
    end = token.find("'", 1) if token.startswith("'") else -1
    if end > 0 and token[end + 1 : end + 2] == "=":
        return token[1:end], token[end + 2 :]
    label, eq, value = token.partition("=")
    return (label, value) if eq else None


def parse_perf_metrics(perf_data: str) -> list[PerfMetric]:
    """Parse a perf_data string into ``[{label, unit}]``, quoted labels intact.

    An entry without a label or a numeric value is left out.
    """
    if len(perf_data) > MAX_PERF_DATA_LENGTH:
        return []
    results: list[PerfMetric] = []
    for token in _PERF_TOKEN_RE.findall(perf_data):
        if (parsed := _label_and_value(token)) is None or not parsed[0]:
            continue
        label, value = parsed
        if (number := _VALUE_RE.match(value.split(";", 1)[0])) is None:
            continue
        results.append({"label": label, "unit": number.group(1)})
    return results
