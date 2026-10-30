#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime, timedelta, UTC

from cmk.ccc.user import UserId
from cmk.gui.oauth.token.token_store import get_token_store
from cmk.gui.scopes import DEFAULT_SCOPE


def _issue_token(user_id: UserId, client_id: str) -> str:
    with get_token_store() as store:
        token = store.issue_token(
            user_id,
            expires_at=datetime.now(UTC) + timedelta(minutes=60),
            resource=None,
            scope=DEFAULT_SCOPE,
            client_id=client_id,
        )
    assert token.is_ok()
    return token.ok.access


def _token_hash(token: str) -> str:
    with get_token_store() as store:
        record = store.get_by_token(token)
    assert record is not None
    return record.token_hash


def _is_token_alive(token: str) -> bool:
    with get_token_store() as store:
        return store.get_by_token(token) is not None
