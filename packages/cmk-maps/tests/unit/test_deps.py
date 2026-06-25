#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Capability predicates that gate every Maps API request.

The daemon does no RBAC of its own — it trusts the capabilities baked into the
ticket by the GUI. These predicates translate that ``Principal`` into the
allow/deny decisions the routers and guard dependencies enforce.
"""

import asyncio

import pytest
from fastapi import HTTPException

from cmk.maps.backend.api.v1.deps import (
    can_configure,
    can_create_map,
    can_run_command,
    rate_limited_read,
    resolve_auth_user,
)
from cmk.maps.backend.core.auth import Principal
from cmk.maps.backend.core.ratelimit import rest_read_limiter


def test_configure_requires_configure_cap() -> None:
    assert can_configure(Principal(name="a", configure=True))
    assert not can_configure(Principal(name="a", configure=False))


def test_create_map_follows_may_edit() -> None:
    # Per-map view/edit is enforced GUI-side; the daemon only needs the
    # general.edit_map grant to admit map creation.
    assert can_create_map(Principal(name="a", may_edit=True))
    assert not can_create_map(Principal(name="a", may_edit=False))


def test_run_command_checks_baked_in_command_set() -> None:
    p = Principal(name="a", commands=frozenset({"acknowledge"}))
    assert can_run_command(p, "acknowledge")
    assert not can_run_command(p, "schedule_downtime")


def test_resolve_auth_user_scopes_unless_see_all() -> None:
    # see_all (admin / general.see_all) bypasses Livestatus contact-group scoping.
    assert resolve_auth_user(Principal(name="alice", see_all=True)) is None
    assert resolve_auth_user(Principal(name="alice", see_all=False)) == "alice"


def test_rate_limited_read_allows_within_budget() -> None:
    user = Principal(name="light")
    assert asyncio.run(rate_limited_read(user)) is user


def test_rate_limited_read_blocks_after_budget() -> None:
    # A valid ticket must not be able to drive unbounded Livestatus load: once
    # the per-user budget is spent, the expensive readers answer 429.
    user = Principal(name="heavy")
    for _ in range(rest_read_limiter._max):  # noqa: SLF001
        rest_read_limiter.record(user.name)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(rate_limited_read(user))
    assert exc.value.status_code == 429


def test_rate_limited_read_is_per_user() -> None:
    # One user's flood must not lock out another (keyed by ticket identity).
    heavy = Principal(name="floods")
    for _ in range(rest_read_limiter._max):  # noqa: SLF001
        rest_read_limiter.record(heavy.name)
    assert asyncio.run(rate_limited_read(Principal(name="innocent"))).name == "innocent"
