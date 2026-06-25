#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Shared GUI↔daemon dyngroup Livestatus-filter validation for Checkmk Maps.

A dyngroup object carries a raw Livestatus filter that both the daemon
(``cmk.maps.backend``, at the map-schema layer) and the GUI
(``cmk.maps.gui``, before splicing it into an on-demand LQL query) must
sanitise identically — otherwise an escaped newline could smuggle in
``Stats:``/``Columns:``/``GET`` headers that change the query semantics or
exfiltrate data. Neither component may import the other (module-layer
boundary), so the allowlist lives here in ``cmk.maps.shared`` — the same seam as
``cmk.maps.shared.states`` / ``cmk.maps.shared.ticket``.

The check itself is transport-neutral and raises ``ValueError``; the GUI
wraps it to re-raise ``MKUserError`` for its request context.
"""

import re
from typing import Final

# Only the safe filter-combinator headers may appear — anything else (Stats:,
# Columns:, OutputFormat:, GET, AuthUser:, …) would change the query semantics
# or exfiltrate data.
SAFE_FILTER_LINE_RE: Final = re.compile(r"^(?:Filter|And|Or|Negate): .+$")

# ``splitlines()`` covers every real line terminator but not NUL, and ``.+``
# matches one — so a NUL would survive into the query. It cannot forge a header,
# but the C++ Livestatus side need not treat it as an ordinary byte.
_CONTROL_CHARS: Final = re.compile(r"[\x00-\x08\x0e-\x1f\x7f]")


def normalize_object_filter(value: str) -> str:
    """Validate and canonicalise a dyngroup Livestatus filter.

    NagVis stores filters with literal ``\\n`` separators and unescapes them at
    query time, so a single Filter: line often arrives without a real newline.
    We normalise to real newlines and require every logical line to be a safe
    combinator header — otherwise an escaped newline could smuggle in
    ``Stats:``/``Columns:``/``GET`` headers (a naive ``[^\\n]+`` regex would let
    the literal ``\\n`` through untouched).

    Raises ``ValueError`` if any line is not a safe combinator header.
    """
    if _CONTROL_CHARS.search(value):
        raise ValueError("object_filter must not contain control characters")
    lines = [ln.strip() for ln in value.replace("\\n", "\n").splitlines() if ln.strip()]
    if not lines or not all(SAFE_FILTER_LINE_RE.fullmatch(ln) for ln in lines):
        raise ValueError("object_filter must be one or more 'Filter: …' lines")
    return "\n".join(lines) + "\n"
