#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sqlite3
import threading

from cmk.gui.oauth.store.backend import initialize_database, oauth_db_path, open_connection
from cmk.gui.oauth.store.client_store import ClientStore
from cmk.gui.oauth.store.token_store import looks_like_token, TokenStore

__all__ = ["client_store", "token_store", "looks_like_token"]


# The OAuth stores share one sqlite connection per worker process: opened on
# first use, reused for the rest of the process's lifetime, never closed.
_connection_lock = threading.Lock()
_connection: sqlite3.Connection | None = None


def _get_connection() -> sqlite3.Connection:
    global _connection
    if _connection is None:
        # The lock only guards against a first-use race between threads.
        with _connection_lock:
            if _connection is None:
                db_path = oauth_db_path()
                initialize_database(db_path)
                _connection = open_connection(db_path)
    return _connection


def token_store() -> TokenStore:
    """Get the token store, backed by the shared per-process connection."""
    return TokenStore(_get_connection())


def client_store() -> ClientStore:
    """Get the registered-client store, backed by the shared per-process connection."""
    return ClientStore(_get_connection())
