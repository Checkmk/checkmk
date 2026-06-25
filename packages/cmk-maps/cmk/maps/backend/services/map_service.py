#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""In-memory map cache for the SSE state relay.

Map *config* is owned by the GUI visuals store. The daemon keeps maps in
memory only so its state/SSE path can resolve them: the SPA registers the map
it loaded (``register_map``) before opening the stream, and the state endpoints
read it back (``get_map``). Nothing here reads or writes map config on disk —
persistence lives entirely in the GUI (pre-visuals on-disk ``.json`` maps are
migrated into the visuals store by ``cmk.update_config`` on update).
"""

from __future__ import annotations

import threading
from collections import OrderedDict

from cmk.maps.backend.schemas.map import MapConfig

# Keyed by (owner, name): maps are per-user visuals, so two users can each own a
# map called "x" and keying by name alone would let one shadow the other in every
# state/SSE stream. The owner is the MAP owner, never the viewer.
#
# Bounded LRU because ``register`` needs only authentication: without a cap one
# authenticated user could loop it with unique names and grow the daemon heap
# without bound. Evicting is safe — the config lives in the GUI store and a
# viewer whose entry was evicted re-registers on its next request.
_CACHE_MAX_ENTRIES = 1024
_CACHE: OrderedDict[tuple[str, str], MapConfig] = OrderedDict()
_CACHE_GUARD = threading.Lock()


def register_map(owner: str, cfg: MapConfig) -> None:
    """Cache a GUI-owned map config in memory for state streaming.

    Map config is owned by the GUI visuals store now; the daemon only needs the
    config in memory so its state/SSE path can resolve and stream it. The SPA
    registers the map it loaded (keyed by the map's owner + name) before opening
    the stream.
    """
    with _CACHE_GUARD:
        _CACHE[(owner, cfg.name)] = cfg
        _CACHE.move_to_end((owner, cfg.name))
        while len(_CACHE) > _CACHE_MAX_ENTRIES:
            _CACHE.popitem(last=False)


def get_map(owner: str, name: str) -> MapConfig | None:
    with _CACHE_GUARD:
        cached = _CACHE.get((owner, name))
        if cached is not None:
            _CACHE.move_to_end((owner, name))
        if cached is None and not owner:
            # Name-only fallback ONLY for the owner-less nested map-link roll-up
            # (state_service passes owner=""). A request that carries a real owner
            # must match exactly, so a user can never pull another user's
            # (possibly private) map config by guessing its name.
            for (_cached_owner, cached_name), cfg in _CACHE.items():
                if cached_name == name:
                    cached = cfg
                    break
    return cached.model_copy(deep=True) if cached is not None else None
