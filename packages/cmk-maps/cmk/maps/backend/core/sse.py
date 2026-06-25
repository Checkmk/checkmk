#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""SSE subscription manager.

Each subscriber owns an ``asyncio.Queue`` of pre-formatted SSE messages. The
broadcast loop computes one delta per (map, auth_user) and ``put_nowait``s
into the matching subscriber queues, so a subscriber costs no extra fetch.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cmk.maps.backend.integrations.checkmk import FolderScope

logger = logging.getLogger(__name__)


@dataclass(eq=False)
class Subscriber:
    # ``auth_user`` is the Livestatus monitoring scope (None = see all hosts).
    # ``folder_scope`` is the independent SETUP-folder read scope. ``group_key``
    # collapses both into one identity so subscribers that would render the SAME
    # map share a single computation+delta — for foldertree maps admin and a
    # see-all guest have the same auth_user (None) but different folder_scope, so
    # the key keeps them apart; for other maps it is just the auth_user.
    auth_user: str | None
    folder_scope: FolderScope | None = None
    group_key: str | None = None
    queue: asyncio.Queue[str] = field(default_factory=lambda: asyncio.Queue(maxsize=64))
    # Set when the client fell so far behind that its queue overflowed. The SSE
    # handler ends the stream on the next wake so the browser reconnects and gets
    # a full resend — see ``push``.
    overflowed: bool = False
    # A freshly (re)joined subscriber needs one full state, not a delta against
    # the group snapshot (which already absorbed changes since its REST first
    # paint). The broadcast loop sends it a full built from the same fetch and
    # clears this, so a reconnect re-fulls only this client, not the whole group.
    needs_full: bool = True


class SubscriptionManager:
    def __init__(self) -> None:
        self._subscribers: dict[str, set[Subscriber]] = {}

    def subscribe(
        self,
        the_map: str,
        auth_user: str | None,
        folder_scope: FolderScope | None = None,
        group_key: str | None = None,
    ) -> Subscriber:
        sub = Subscriber(
            auth_user=auth_user,
            folder_scope=folder_scope,
            group_key=group_key if group_key is not None else auth_user,
        )
        self._subscribers.setdefault(the_map, set()).add(sub)
        logger.debug(
            "SSE subscribe map=%(map)s user=%(user)s key=%(key)s total=%(total)d",
            {
                "map": the_map,
                "user": auth_user,
                "key": sub.group_key,
                "total": len(self._subscribers[the_map]),
            },
        )
        return sub

    def unsubscribe(self, the_map: str, sub: Subscriber) -> None:
        subs = self._subscribers.get(the_map, set())
        subs.discard(sub)
        if not subs:
            self._subscribers.pop(the_map, None)
        logger.debug(
            "SSE unsubscribe map=%(map)s remaining=%(remaining)d",
            {"map": the_map, "remaining": len(subs)},
        )

    def get_subscriber_count(self, the_map: str) -> int:
        return len(self._subscribers.get(the_map, ()))

    def get_subscribers_grouped(self, the_map: str) -> dict[str | None, list[Subscriber]]:
        # Grouped by ``group_key`` (auth_user + folder scope), not auth_user alone,
        # so users with different rendered output (e.g. admin vs see-all guest on a
        # foldertree map) get their own computation + delta stream.
        groups: dict[str | None, list[Subscriber]] = {}
        for sub in self._subscribers.get(the_map, ()):
            groups.setdefault(sub.group_key, []).append(sub)
        return groups

    def push(self, the_map: str, targets: list[Subscriber], message: str) -> None:
        """Put *message* into each target's queue, or flag an overflowed client.

        The stream carries incremental deltas (added/changed/removed), so silently
        dropping a payload for a slow client would leave it showing stale state
        indefinitely — there is no per-subscriber catch-up. A full queue therefore
        means the client fell too far behind: flag it so the SSE handler ends the
        stream (never blocking the broadcast loop), and the browser reconnects and
        gets a full resend via the drop-snapshot-on-join in ``sse_map_states``.
        """
        for sub in targets:
            try:
                sub.queue.put_nowait(message)
            except asyncio.QueueFull:
                if not sub.overflowed:
                    logger.warning(
                        "SSE client fell behind (queue full) for map=%(map)s; "
                        "ending stream to force a reconnect + full resend",
                        {"map": the_map},
                    )
                sub.overflowed = True


manager = SubscriptionManager()
