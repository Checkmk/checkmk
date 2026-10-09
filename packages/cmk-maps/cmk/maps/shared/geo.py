#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Shared GUI↔daemon host geo-coordinate resolution for Checkmk Maps.

Both the daemon (``cmk.maps.backend``, for the worldmap automap source) and the
GUI (``cmk.maps.gui``, for single-host editor placement) turn a host's
monitoring data into ``(lat, lng)`` using the same source order: the
``maps_lat``/``maps_lng`` host labels first, then the legacy ``LAT``/``LONG``
custom variables as a fallback. Neither component may import the other
(module-layer boundary), so the keys + resolution live here in ``cmk.maps.shared`` —
the same seam as ``cmk.maps.shared.states``.
"""

import re
from collections.abc import Mapping
from typing import Final

# Host geo-coordinate sources, in resolution order.
LAT_LABEL: Final = "maps_lat"
LNG_LABEL: Final = "maps_lng"
LAT_VAR: Final = "LAT"
LNG_VAR: Final = "LONG"

LAT_LIMIT: Final = 90.0
LNG_LIMIT: Final = 180.0


# A plain decimal degree. ``float()`` alone would also take "nan", "inf",
# exponents and digit-grouping underscores ("48_1" is 481.0).
_DEGREES: Final = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)", re.ASCII)


def _to_degrees(value: object, limit: float) -> float | None:
    if value is None or not _DEGREES.fullmatch(text := str(value).strip()):
        return None
    degrees = float(text)
    return degrees if -limit <= degrees <= limit else None


def to_coords(lat: object, lng: object) -> tuple[float, float] | None:
    """``(lat, lng)`` if both are plain decimal degrees within range, else ``None``."""
    lat_degrees = _to_degrees(lat, LAT_LIMIT)
    lng_degrees = _to_degrees(lng, LNG_LIMIT)
    if lat_degrees is None or lng_degrees is None:
        return None
    return lat_degrees, lng_degrees


def resolve_host_coords(
    labels: Mapping[str, object], custom_vars: Mapping[str, object]
) -> tuple[float, float] | None:
    """Resolve ``(lat, lng)`` from a host's labels, falling back to custom vars.

    The ``maps_lat``/``maps_lng`` labels win; if either is missing, not a
    decimal number or out of range, the legacy ``LAT``/``LONG`` custom variables are tried.
    Returns ``None`` when no usable pair is found.
    """
    return to_coords(labels.get(LAT_LABEL), labels.get(LNG_LABEL)) or to_coords(
        custom_vars.get(LAT_VAR), custom_vars.get(LNG_VAR)
    )
