#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from pathlib import Path

import pytest
from dateutil.relativedelta import relativedelta

from cmk.ccc.user import UserId
from cmk.gui.token_auth import DashboardToken, TokenStore
from cmk.gui.token_auth._store import InvalidToken, TokenExpired, TokenRevoked

some_time = datetime.datetime(2020, 1, 20, 20, 20, 20, tzinfo=datetime.UTC)


def test_successful_verification(tmp_path: Path) -> None:
    store = TokenStore(tmp_path / "store.json")
    token = store.issue(
        token_details=DashboardToken(
            owner=UserId("owner"),
            dashboard_name="unit-dashboard",
        ),
        issuer=UserId("issuer"),
        now=some_time,
        valid_for=relativedelta(days=1),
    )
    store.verify(f"0:{token.token_id}", now=some_time)


def test_revokation(tmp_path: Path) -> None:
    store = TokenStore(tmp_path / "store.json")
    token = store.issue(
        token_details=DashboardToken(
            owner=UserId("owner"),
            dashboard_name="unit-dashboard",
        ),
        issuer=UserId("issuer"),
        now=some_time,
        valid_for=relativedelta(days=1),
    )
    store.revoke(token.token_id)

    with pytest.raises(TokenRevoked):
        store.verify(f"0:{token.token_id}", now=some_time)


def test_expired(tmp_path: Path) -> None:
    store = TokenStore(tmp_path / "store.json")
    token = store.issue(
        token_details=DashboardToken(
            owner=UserId("owner"),
            dashboard_name="unit-dashboard",
        ),
        issuer=UserId("issuer"),
        now=some_time,
        valid_for=relativedelta(days=1),
    )

    with pytest.raises(TokenExpired):
        store.verify(f"0:{token.token_id}", now=some_time + datetime.timedelta(days=1, seconds=1))


def test_invalid_token(tmp_path: Path) -> None:
    store = TokenStore(tmp_path / "store.json")

    with pytest.raises(InvalidToken, match="Could not parse token"):
        store.verify("invalid", now=some_time)

    with pytest.raises(InvalidToken, match="Invalid token version 'invalid'"):
        store.verify("invalid:also invalid", now=some_time)

    with pytest.raises(InvalidToken, match="Could not find token 'foo'"):
        store.verify("0:foo", now=some_time)


def test_issued_at(tmp_path: Path) -> None:
    store = TokenStore(tmp_path / "store.json")
    token = store.issue(
        token_details=DashboardToken(
            owner=UserId("owner"),
            dashboard_name="unit-dashboard",
        ),
        issuer=UserId("issuer"),
        now=some_time,
        valid_for=relativedelta(days=1),
    )
    assert token.issued_at == some_time
