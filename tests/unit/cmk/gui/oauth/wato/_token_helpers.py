#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime, timedelta, UTC

from cmk.ccc.user import UserId
from cmk.gui.oauth.token.token_store import get_token_store, IssuedTokens
from cmk.gui.scopes import DEFAULT_SCOPE


def _start_grant(user_id: UserId, client_id: str) -> IssuedTokens:
    now = datetime.now(UTC)
    with get_token_store() as store:
        issued = store.start_grant(
            user_id,
            resource=None,
            scope=DEFAULT_SCOPE,
            client_id=client_id,
            expires_at=now + timedelta(days=365),
            refresh_token_expires_at=now + timedelta(days=30),
            access_token_expires_at=now + timedelta(hours=48),
        )
    assert issued.is_ok()
    return issued.ok


def _grant_id(issued: IssuedTokens) -> str:
    with get_token_store() as store:
        record = store.get_refresh_token(issued.refresh)
    assert record is not None
    return record.grant.grant_id


def _is_session_alive(issued: IssuedTokens) -> bool:
    with get_token_store() as store:
        return store.get_refresh_token(issued.refresh) is not None
