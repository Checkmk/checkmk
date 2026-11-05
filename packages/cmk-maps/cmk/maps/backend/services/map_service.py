#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""In-memory map cache for the SSE state relay.

Map *config* is owned by the GUI visuals store. The daemon keeps maps in
memory only so its state/SSE path can resolve them: the SPA registers the map
it loaded (``register_map``) before opening the stream, and the state endpoints
read it back (``get_map``). Nothing here reads or writes map config on disk —
persistence lives entirely in the GUI.
"""

import threading
import time
from collections import OrderedDict
from collections.abc import Mapping, Sequence
from collections.abc import Set as AbstractSet
from typing import Protocol

from cmk.maps.backend.core.auth import LinkTarget
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


# The highest version of each map registered signed. Kept for more maps than the
# cache holds, so a map pushed out of it still refuses an older config.
_SIGNED_VERSIONS_MAX_ENTRIES = 10 * _CACHE_MAX_ENTRIES
_SIGNED_VERSIONS: OrderedDict[tuple[str, str], int] = OrderedDict()


def register_map(owner: str, cfg: MapConfig) -> None:
    """Cache a GUI-owned map config in memory for state streaming.

    Map config is owned by the GUI visuals store now; the daemon only needs the
    config in memory so its state/SSE path can resolve and stream it. The SPA
    registers the map it loaded (keyed by the map's owner + name) before opening
    the stream.
    """
    with _CACHE_GUARD:
        _cache(owner, cfg)


def register_signed_map(owner: str, cfg: MapConfig) -> bool:
    """Like :func:`register_map` for a config the GUI signed, unless one with a
    later version was registered: return whether it was."""
    key = (owner, cfg.name)
    with _CACHE_GUARD:
        if cfg.version < _SIGNED_VERSIONS.get(key, cfg.version):
            return False
        _put_bounded(_SIGNED_VERSIONS, key, cfg.version, _SIGNED_VERSIONS_MAX_ENTRIES)
        _cache(owner, cfg)
    return True


def _cache(owner: str, cfg: MapConfig) -> None:
    _put_bounded(_CACHE, (owner, cfg.name), cfg, _CACHE_MAX_ENTRIES)


def _put_bounded[K, V](entries: OrderedDict[K, V], key: K, value: V, limit: int) -> None:
    entries[key] = value
    entries.move_to_end(key)
    while len(entries) > limit:
        entries.popitem(last=False)


def get_map(owner: str, name: str) -> MapConfig | None:
    """The map registered under exactly this owner.

    Every viewer and request of the map shares it, so callers derive a changed
    config with ``model_copy(update=...)`` instead of changing it.
    """
    with _CACHE_GUARD:
        cached = _CACHE.get((owner, name))
        if cached is not None:
            _CACHE.move_to_end((owner, name))
    return cached


# Maps fetched only because a link names them. Kept apart, so they never push a
# map someone has open out of the cache, and fetched again after a while, so a
# change that reached no open view reaches the links too.
_LINKED_FOR = 300.0
_LINKED: OrderedDict[tuple[str, str], tuple[float, MapConfig]] = OrderedDict()


class LinkSource(Protocol):
    async def link_targets(
        self,
        as_user: str,
        names: Sequence[str],
        held: AbstractSet[tuple[str, str]],
        *,
        now: float,
    ) -> Mapping[str, LinkTarget]: ...


async def find_link_targets(
    source: LinkSource, as_user: str, names: Sequence[str]
) -> dict[str, tuple[str, MapConfig]]:
    """The maps ``as_user`` sees under the names map links give, by name.

    A link names its target without an owner and means the map the user would
    open under that name. A target the daemon does not hold is fetched.
    """
    wanted = set(names)
    now = time.monotonic()
    with _CACHE_GUARD:
        held = {key for key in _CACHE if key[1] in wanted}
        held.update(
            key
            for key, (fetched_at, _cfg) in _LINKED.items()
            if key[1] in wanted and now - fetched_at < _LINKED_FOR
        )
    found: dict[str, tuple[str, MapConfig]] = {}
    for name, target in (await source.link_targets(as_user, names, held, now=now)).items():
        key = (target.owner, name)
        with _CACHE_GUARD:
            if target.config is not None:
                _LINKED[key] = (now, target.config)
                _LINKED.move_to_end(key)
                while len(_LINKED) > _CACHE_MAX_ENTRIES:
                    _LINKED.popitem(last=False)
            cfg = _CACHE.get(key) or _LINKED.get(key, (0.0, None))[1]
        if cfg is not None:
            found[name] = (target.owner, cfg)
    return found
