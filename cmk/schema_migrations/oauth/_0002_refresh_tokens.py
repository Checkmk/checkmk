#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from sqlite3 import Connection
from typing import override

from cmk.schema_manager import Revision

_REFRESH_TOKENS_SQL = """
CREATE TABLE IF NOT EXISTS grants (
    grant_id TEXT PRIMARY KEY NOT NULL,
    user_id TEXT NOT NULL CHECK (user_id <> ''),
    client_id TEXT NOT NULL CHECK (client_id <> '')
        REFERENCES clients(client_id) ON DELETE CASCADE,
    resource TEXT,
    scope TEXT,
    created_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL,
    CHECK (expires_at > created_at)
);

CREATE INDEX IF NOT EXISTS idx_grants_user_id_created_at
    ON grants (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_grants_client_id
    ON grants (client_id);

CREATE TABLE IF NOT EXISTS refresh_tokens (
    token_hash TEXT PRIMARY KEY NOT NULL CHECK (length(token_hash) = 64),
    grant_id TEXT NOT NULL
        REFERENCES grants(grant_id) ON DELETE CASCADE,
    issued_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL,
    rotated_at INTEGER,
    CHECK (expires_at > issued_at)
);

CREATE INDEX IF NOT EXISTS idx_refresh_tokens_grant_id
    ON refresh_tokens (grant_id);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_expires_at
    ON refresh_tokens (expires_at);

-- Only adds a nullable column, so the tokens table is not rewritten.
ALTER TABLE tokens ADD COLUMN grant_id TEXT
    REFERENCES grants(grant_id) ON DELETE CASCADE;
CREATE INDEX IF NOT EXISTS idx_tokens_grant_id ON tokens (grant_id);
"""


class RefreshTokens(Revision[Connection]):
    id = "0002"

    @override
    def upgrade(self, connection: Connection) -> None:
        connection.executescript(_REFRESH_TOKENS_SQL)
