#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sqlite3
from http import HTTPStatus

import pytest

from cmk.gui.oauth.token.backend import (
    OAUTH_DATABASE_BACKEND,
    OAUTH_DATABASE_NAME,
    StoreUnavailableError,
)
from cmk.schema_migrations.oauth import schema_manager_oauth
from cmk.testlib.schema_manager import migrated_connection


def _insert_client(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        INSERT INTO clients (client_id, redirect_uris, client_name, registered_at)
        VALUES ('test-client', '[]', NULL, 0)
        """
    )


def test_an_unavailable_store_is_a_service_unavailable_response() -> None:
    # No page catches StoreUnavailableError: both WSGI applications answer an
    # MKHTTPException with its status, which is what keeps an unusable
    # database from becoming a crash report per request.
    assert StoreUnavailableError("").status == HTTPStatus.SERVICE_UNAVAILABLE


def test_the_runtime_connects_to_the_migrated_database() -> None:
    assert schema_manager_oauth.name == OAUTH_DATABASE_NAME
    assert schema_manager_oauth.backend == OAUTH_DATABASE_BACKEND


def test_tokens_table_rejects_a_token_hash_of_the_wrong_length() -> None:
    with migrated_connection(schema_manager_oauth) as connection:
        _insert_client(connection)

        with pytest.raises(sqlite3.IntegrityError, match="length\\(token_hash\\) = 64"):
            connection.execute(
                "INSERT INTO tokens (token_hash, user_id, issued_at, expires_at, client_id)"
                " VALUES (?, ?, ?, ?, ?)",
                ("too-short", "cmkadmin", 0, 100, "test-client"),
            )


def test_tokens_table_rejects_expires_at_not_after_issued_at() -> None:
    with migrated_connection(schema_manager_oauth) as connection:
        _insert_client(connection)

        with pytest.raises(sqlite3.IntegrityError, match="expires_at > issued_at"):
            connection.execute(
                "INSERT INTO tokens (token_hash, user_id, issued_at, expires_at, client_id)"
                " VALUES (?, ?, ?, ?, ?)",
                ("a" * 64, "cmkadmin", 100, 100, "test-client"),
            )
