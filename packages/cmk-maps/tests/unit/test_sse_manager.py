#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Unit tests for the SSE SubscriptionManager.

Covers subscriber bookkeeping, the group_key collapsing that decides which
subscribers share one delta computation, and the overflow flagging in ``push``
when a slow client's queue is full (the SSE handler then ends the stream so the
client reconnects for a full resend). ``Subscriber`` builds its queue on the
running event loop, so the few cases that touch a queue run inside ``asyncio.run``
rather than relying on pytest-asyncio.
"""

import asyncio

from cmk.maps.backend.core.sse import Subscriber, SubscriptionManager


def test_subscribe_tracks_and_counts() -> None:
    mgr = SubscriptionManager()
    sub = mgr.subscribe("map1", "alice")
    assert mgr.get_subscriber_count("map1") == 1
    # group_key defaults to auth_user when not given explicitly.
    assert sub.group_key == "alice"


def test_subscriber_needs_full_by_default() -> None:
    # A fresh subscriber must get one full state before deltas; the broadcast loop
    # reads this flag to re-full only the newcomer, not the whole group.
    mgr = SubscriptionManager()
    sub = mgr.subscribe("map1", "alice")
    assert sub.needs_full is True


def test_explicit_group_key_is_kept() -> None:
    mgr = SubscriptionManager()
    sub = mgr.subscribe("map1", None, group_key="admin-folderscope")
    assert sub.group_key == "admin-folderscope"


def test_unsubscribe_removes_and_drops_empty_map() -> None:
    mgr = SubscriptionManager()
    sub = mgr.subscribe("map1", "alice")
    mgr.unsubscribe("map1", sub)
    assert mgr.get_subscriber_count("map1") == 0
    # Map key removed entirely once the last subscriber leaves.
    assert "map1" not in mgr._subscribers  # noqa: SLF001


def test_unsubscribe_unknown_is_noop() -> None:
    mgr = SubscriptionManager()
    mgr.unsubscribe("ghost", Subscriber(auth_user="x"))
    assert mgr.get_subscriber_count("ghost") == 0


def test_same_auth_user_different_group_key_split() -> None:
    # Foldertree map: admin and a see-all guest share auth_user None but
    # render differently, so distinct group_keys keep them in separate groups.
    mgr = SubscriptionManager()
    mgr.subscribe("map1", None, group_key="admin")
    mgr.subscribe("map1", None, group_key="guest")
    groups = mgr.get_subscribers_grouped("map1")
    assert set(groups) == {"admin", "guest"}
    assert all(len(v) == 1 for v in groups.values())


def test_same_group_key_shares_one_group() -> None:
    mgr = SubscriptionManager()
    mgr.subscribe("map1", "user1")
    mgr.subscribe("map1", "user1")
    groups = mgr.get_subscribers_grouped("map1")
    assert set(groups) == {"user1"}
    assert len(groups["user1"]) == 2


def test_empty_map_yields_no_groups() -> None:
    assert SubscriptionManager().get_subscribers_grouped("none") == {}


def test_push_delivers_message_to_each_target() -> None:
    async def scenario() -> None:
        mgr = SubscriptionManager()
        a = mgr.subscribe("map1", "a")
        b = mgr.subscribe("map1", "b")
        mgr.push("map1", [a, b], "data: x\n\n")
        assert a.queue.get_nowait() == "data: x\n\n"
        assert b.queue.get_nowait() == "data: x\n\n"

    asyncio.run(scenario())


def test_push_full_queue_flags_overflow() -> None:
    # The stream carries incremental deltas, so silently dropping a payload for a
    # slow client would leave it permanently stale. A full queue instead flags the
    # subscriber as overflowed (the SSE handler ends the stream → reconnect → full
    # resend) without blocking the broadcast loop.
    async def scenario() -> None:
        sub = Subscriber(auth_user="slow", queue=asyncio.Queue(maxsize=1))
        sub.queue.put_nowait("old")
        mgr = SubscriptionManager()
        mgr.push("map1", [sub], "new")
        assert sub.overflowed is True
        # Nothing is silently dropped; the queue is left untouched for teardown.
        assert sub.queue.get_nowait() == "old"

    asyncio.run(scenario())


def test_push_healthy_queue_does_not_flag_overflow() -> None:
    async def scenario() -> None:
        sub = Subscriber(auth_user="ok", queue=asyncio.Queue(maxsize=2))
        mgr = SubscriptionManager()
        mgr.push("map1", [sub], "m1")
        assert sub.overflowed is False
        assert sub.queue.get_nowait() == "m1"

    asyncio.run(scenario())
