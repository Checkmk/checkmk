#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import hashlib
from datetime import datetime, timedelta, UTC
from sqlite3 import Connection
from typing import override

from cmk.gui.oauth.token.token_store import TokenStore
from cmk.schema_manager import ManagedDatabase
from cmk.schema_migrations.oauth import schema_manager_oauth
from cmk.testlib.schema_manager import RevisionTestSuite


class TestOauthRevisions(RevisionTestSuite[Connection]):
    @property
    @override
    def managed_database(self) -> ManagedDatabase[Connection]:
        return schema_manager_oauth

    def test_access_token_from_before_0002_keeps_working_without_a_grant(self) -> None:
        access_token = "cmko1.issued-before-the-update"
        now = int(datetime.now(UTC).timestamp())
        connection = self.apply_up_to("0001")
        connection.execute(
            "INSERT INTO clients (client_id, redirect_uris, registered_at) VALUES ('c', '[]', 0)"
        )
        connection.execute(
            """
            INSERT INTO tokens
                (token_hash, user_id, issued_at, expires_at, resource, scope, client_id)
            VALUES (?, 'cmkadmin', ?, ?, NULL, 'read', 'c')
            """,
            (
                hashlib.sha256(access_token.encode("utf-8")).hexdigest(),
                now,
                now + int(timedelta(hours=48).total_seconds()),
            ),
        )

        self.apply_up_to("0002")

        record = TokenStore(connection).get_by_token(access_token)
        assert record is not None
        assert record.is_valid()
