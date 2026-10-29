#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.fastapi.gui_session import IdentityCache


def test_a_user_id_is_known_until_the_ttl_has_passed() -> None:
    cache = IdentityCache[str](ttl=60)
    cache.put("cookie", "jdoe", now=1000.0)

    assert [cache.get("cookie", now=t) for t in (1000.0, 1059.9, 1060.0)] == [
        "jdoe",
        "jdoe",
        None,
    ]


def test_another_cookie_is_not_known() -> None:
    cache = IdentityCache[str](ttl=60)
    cache.put("cookie", "jdoe", now=1000.0)

    assert cache.get("other cookie", now=1000.0) is None


def test_an_expired_entry_is_dropped_when_it_is_looked_up() -> None:
    cache = IdentityCache[str](ttl=60)
    cache.put("cookie", "jdoe", now=1000.0)

    cache.get("cookie", now=1060.0)

    assert len(cache) == 0


def test_expired_entries_are_dropped_when_another_is_added() -> None:
    cache = IdentityCache[str](ttl=60)
    cache.put("old cookie", "jdoe", now=1000.0)
    cache.put("valid cookie", "jdoe", now=1030.0)

    cache.put("new cookie", "hdoe", now=1060.0)

    assert len(cache) == 2


def test_a_new_answer_replaces_the_old_one() -> None:
    cache = IdentityCache[str](ttl=60)
    cache.put("cookie", "jdoe", now=1000.0)

    cache.put("cookie", "hdoe", now=1050.0)

    assert cache.get("cookie", now=1100.0) == "hdoe"
