#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from sqlite3 import Connection
from typing import override

from cmk.schema_manager import Revision

_INITIAL_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS clients (
    client_id TEXT PRIMARY KEY NOT NULL CHECK (client_id <> ''),
    redirect_uris TEXT NOT NULL,
    client_name TEXT,
    registered_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS tokens (
    token_hash TEXT PRIMARY KEY NOT NULL CHECK (length(token_hash) = 64),
    user_id TEXT NOT NULL CHECK (user_id <> ''),
    issued_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL,
    resource TEXT,
    scope TEXT,
    client_id TEXT NOT NULL CHECK (client_id <> '')
        REFERENCES clients(client_id) ON DELETE CASCADE,
    CHECK (expires_at > issued_at)
);

CREATE INDEX IF NOT EXISTS idx_tokens_user_id_issued_at
    ON tokens (user_id, issued_at DESC);

CREATE INDEX IF NOT EXISTS idx_tokens_expires_at
    ON tokens (expires_at);

-- Deleting a client cascades into tokens. Without this index that is a
-- full-table scan per deleted client.
CREATE INDEX IF NOT EXISTS idx_tokens_client_id
    ON tokens (client_id);
"""


class InitialSchema(Revision[Connection]):
    id = "0001"

    @override
    def upgrade(self, connection: Connection) -> None:
        connection.executescript(_INITIAL_SCHEMA_SQL)
