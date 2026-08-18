#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui import userdb
from cmk.gui.oauth.store.token_store import get_token_store, TokenRecord
from cmk.gui.userdb import load_user


def active_token(token: str) -> TokenRecord | None:
    with get_token_store() as store:
        record = store.get_by_token(token)
    if record is None or not record.is_valid():
        return None

    if not userdb.user_exists(record.user_id) or userdb.user_locked(
        record.user_id, load_user(record.user_id)
    ):
        return None

    return record
