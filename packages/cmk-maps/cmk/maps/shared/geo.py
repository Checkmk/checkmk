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

from collections.abc import Mapping
from typing import Final

# Host geo-coordinate sources, in resolution order.
LAT_LABEL: Final = "maps_lat"
LNG_LABEL: Final = "maps_lng"
LAT_VAR: Final = "LAT"
LNG_VAR: Final = "LONG"


def _to_coords(lat: object, lng: object) -> tuple[float, float] | None:
    if lat is None or lng is None:
        return None
    try:
        return float(str(lat)), float(str(lng))
    except TypeError, ValueError:
        return None


def resolve_host_coords(
    labels: Mapping[str, object], custom_vars: Mapping[str, object]
) -> tuple[float, float] | None:
    """Resolve ``(lat, lng)`` from a host's labels, falling back to custom vars.

    The ``maps_lat``/``maps_lng`` labels win; if either is missing or not a
    parseable number, the legacy ``LAT``/``LONG`` custom variables are tried.
    Returns ``None`` when no usable pair is found.
    """
    return _to_coords(labels.get(LAT_LABEL), labels.get(LNG_LABEL)) or _to_coords(
        custom_vars.get(LAT_VAR), custom_vars.get(LNG_VAR)
    )
