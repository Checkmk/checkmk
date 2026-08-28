#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import secrets
import sqlite3
from collections.abc import Collection, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, UTC
from typing import NewType

from cmk.ccc.resulttype import Error, OK, Result
from cmk.gui.oauth.store.backend import Backend, connect, oauth_db_path

_MAX_REGISTERED_CLIENTS = 1000

ClientId = NewType("ClientId", str)


@dataclass(frozen=True, slots=True)
class ClientRegistration:
    """A dynamically registered OAuth client, as persisted to the store."""

    client_id: ClientId
    redirect_uris: list[str]
    # Unauthenticated free text (RFC 7591) -- never render without escaping.
    client_name: str | None
    registered_at: datetime


@dataclass(frozen=True, slots=True)
class RegistryFull:
    """The client store already holds the maximum number of registrations."""


class ClientStore(Backend):
    def register(
        self, redirect_uris: list[str], client_name: str | None
    ) -> Result[ClientRegistration, RegistryFull]:
        """The new registration, or RegistryFull if the store already holds the maximum."""
        with self.write_transaction():
            count = self._connection.execute("SELECT COUNT(*) FROM clients").fetchone()[0]
            if count >= _MAX_REGISTERED_CLIENTS:
                return Error(RegistryFull())

            registered_at_timestamp = int(datetime.now(UTC).timestamp())
            registration = ClientRegistration(
                client_id=ClientId(secrets.token_urlsafe(32)),
                redirect_uris=redirect_uris,
                client_name=client_name,
                registered_at=datetime.fromtimestamp(registered_at_timestamp, tz=UTC),
            )
            self._connection.execute(
                """
                INSERT INTO clients (client_id, redirect_uris, client_name, registered_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    registration.client_id,
                    json.dumps(redirect_uris),
                    client_name,
                    registered_at_timestamp,
                ),
            )
        return OK(registration)

    def get(self, client_id: str) -> ClientRegistration | None:
        row = self._connection.execute(
            """
            SELECT client_id, redirect_uris, client_name, registered_at
            FROM clients
            WHERE client_id = ?
            """,
            (client_id,),
        ).fetchone()

        if row is None:
            return None

        return _row_to_registration(row)

    def list(self) -> list[ClientRegistration]:
        rows = self._connection.execute(
            """
            SELECT client_id, redirect_uris, client_name, registered_at
            FROM clients
            ORDER BY registered_at ASC
            """
        ).fetchall()
        return [_row_to_registration(row) for row in rows]

    def delete(self, client_ids: Collection[str]) -> int:
        unique_ids = set(client_ids)
        if not unique_ids:
            return 0

        with self.write_transaction():
            cursor = self._connection.executemany(
                "DELETE FROM clients WHERE client_id = ?",
                [(client_id,) for client_id in unique_ids],
            )
        return cursor.rowcount


@contextmanager
def get_client_store() -> Iterator[ClientStore]:
    """Get the registered-client store, on a connection closed at the end of the with block."""
    with connect(oauth_db_path()) as connection:
        yield ClientStore(connection)


def _row_to_registration(row: sqlite3.Row) -> ClientRegistration:
    return ClientRegistration(
        client_id=ClientId(row["client_id"]),
        redirect_uris=json.loads(row["redirect_uris"]),
        client_name=row["client_name"],
        registered_at=datetime.fromtimestamp(row["registered_at"], tz=UTC),
    )
