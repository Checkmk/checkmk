#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.ccc.user import UserId
from cmk.gui import userdb
from cmk.gui.oauth.token.token_store import get_token_store, TokenRecord
from cmk.gui.userdb import load_user


def user_can_authenticate(user_id: UserId) -> bool:
    return userdb.user_exists(user_id) and not userdb.user_locked(user_id, load_user(user_id))


def active_token(token: str) -> TokenRecord | None:
    with get_token_store() as store:
        record = store.get_by_token(token)
    if record is None or not record.is_valid():
        return None

    return record if user_can_authenticate(record.user_id) else None
