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

import math
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from collections.abc import Set as AbstractSet
from typing import NamedTuple, Protocol

from cmk.maps.backend.core.auth import LinkTarget
from cmk.maps.backend.core.ttl_cache import TtlCache
from cmk.maps.backend.schemas.map import MapConfig

type MapKey = tuple[str, str]


class _Sized(NamedTuple):
    config: MapConfig
    size: int


def _bytes_sent(entry: _Sized) -> int:
    return entry.size


# Nothing in these caches goes stale by age alone.
_KEPT = math.inf


# Keyed by (owner, name): maps are per-user visuals, so two users can each own a
# map called "x" and keying by name alone would let one shadow the other in every
# state/SSE stream. The owner is the MAP owner, never the viewer.
#
# Bounded because ``register`` needs only authentication: without a cap one
# authenticated user could loop it with unique names and grow the daemon heap
# without bound. A map with an open stream is never evicted, as its broadcast
# loop reads it on every tick; those are bounded by the stream limit. Evicting
# any other is safe — the config lives in the GUI store and a viewer whose
# entry was evicted re-registers on its next request.
_CACHE_MAX_ENTRIES = 1024
# A map may take up to MAP_CONFIG_MAX_BYTES, so the count alone would allow gigabytes.
CACHE_MAX_BYTES = 64 * 1024 * 1024
_CACHE: TtlCache[MapKey, _Sized] = TtlCache(
    maxsize=_CACHE_MAX_ENTRIES, weigh=_bytes_sent, maxweight=CACHE_MAX_BYTES
)
_CACHE_GUARD = threading.Lock()


# The highest version of each map registered signed. Kept for more maps than the
# cache holds, so a map pushed out of it still refuses an older config.
_SIGNED_VERSIONS: TtlCache[MapKey, int] = TtlCache(maxsize=10 * _CACHE_MAX_ENTRIES)


def register_map(
    owner: str, cfg: MapConfig, *, size: int = 0, pinned: Callable[[MapKey], bool] | None = None
) -> None:
    """Cache a GUI-owned map config in memory for state streaming.

    Map config is owned by the GUI visuals store now; the daemon only needs the
    config in memory so its state/SSE path can resolve and stream it. The SPA
    registers the map it loaded (keyed by the map's owner + name) before opening
    the stream. ``size`` is the bytes the config took to send. A map for which
    ``pinned`` holds is not evicted for it.
    """
    with _CACHE_GUARD:
        _CACHE.set((owner, cfg.name), _Sized(cfg, size), pinned=pinned)


def register_signed_map(
    owner: str, cfg: MapConfig, *, size: int = 0, pinned: Callable[[MapKey], bool] | None = None
) -> bool:
    """Like :func:`register_map` for a config the GUI signed, unless one with a
    later version was registered: return whether it was."""
    key = (owner, cfg.name)
    with _CACHE_GUARD:
        registered = _SIGNED_VERSIONS.get(key, ttl=_KEPT)
        if registered is not None and cfg.version < registered:
            return False
        _SIGNED_VERSIONS.set(key, cfg.version)
        _CACHE.set(key, _Sized(cfg, size), pinned=pinned)
    return True


def get_map(owner: str, name: str) -> MapConfig | None:
    """The map registered under exactly this owner.

    Every viewer and request of the map shares it, so callers derive a changed
    config with ``model_copy(update=...)`` instead of changing it.
    """
    with _CACHE_GUARD:
        if (entry := _CACHE.get((owner, name), ttl=_KEPT)) is not None:
            _CACHE.touch((owner, name))
    return None if entry is None else entry.config


def forget_map(owner: str, name: str) -> None:
    """Drop a deleted map, so it is neither served nor linked to any more."""
    with _CACHE_GUARD:
        _CACHE.pop((owner, name))
        _LINKED.pop((owner, name))


# Maps fetched only because a link names them. Kept apart, so they never push a
# map someone has open out of the cache, and fetched again after a while, so a
# change that reached no open view reaches the links too.
_LINKED_FOR = 300.0
_LINKED: TtlCache[MapKey, _Sized] = TtlCache(
    maxsize=_CACHE_MAX_ENTRIES, weigh=_bytes_sent, maxweight=CACHE_MAX_BYTES
)


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
    source: LinkSource,
    as_user: str,
    names: Sequence[str],
    *,
    clock: Callable[[], float] = time.monotonic,
) -> dict[str, tuple[str, MapConfig]]:
    """The maps ``as_user`` sees under the names map links give, by name.

    A link names its target without an owner and means the map the user would
    open under that name. A target the daemon does not hold is fetched.
    """
    wanted = set(names)
    now = clock()
    with _CACHE_GUARD:
        held = {key for key in _CACHE if key[1] in wanted}
        held.update(
            key
            for key in _LINKED
            if key[1] in wanted and _LINKED.get(key, ttl=_LINKED_FOR, now=now) is not None
        )
    found: dict[str, tuple[str, MapConfig]] = {}
    for name, target in (await source.link_targets(as_user, names, held, now=now)).items():
        key = (target.owner, name)
        with _CACHE_GUARD:
            if target.config is not None:
                _LINKED.set(key, _Sized(target.config, target.size), now=now)
            entry = _CACHE.get(key, ttl=_KEPT) or _LINKED.get(key, ttl=_LINKED_FOR, now=now)
            cfg = None if entry is None else entry.config
        if cfg is not None:
            found[name] = (target.owner, cfg)
    return found
