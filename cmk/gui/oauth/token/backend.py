#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from http import HTTPStatus
from typing import Final

from cmk.gui.exceptions import MKHTTPException
from cmk.gui.log import logger
from cmk.schema_manager import BackendUnavailableError
from cmk.schema_manager.backend.sqlite import Sqlite

# Must match cmk.schema_migrations.oauth, which the runtime may not import.
OAUTH_DATABASE_NAME: Final = "oauth"
OAUTH_DATABASE_BACKEND: Final = Sqlite()


class StoreUnavailableError(MKHTTPException):
    """The OAuth database cannot be opened, or is not one we can work with.

    Only cmk.gui.oauth.find_access_token catches this; everywhere else both
    WSGI applications answer an MKHTTPException with its status, so an
    unusable database costs a 503 per request instead of a crash report.
    Whoever raises it logs the reason -- the message here also reaches
    unauthenticated clients.
    """

    status = HTTPStatus.SERVICE_UNAVAILABLE  # type: ignore[mutable-override]


_UNAVAILABLE = "The OAuth database is unavailable. See var/log/web.log for details."


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    """Connect to the OAuth database; database errors surface as `StoreUnavailableError`."""
    try:
        with OAUTH_DATABASE_BACKEND.connect(OAUTH_DATABASE_NAME) as connection:
            try:
                yield connection
            except sqlite3.Error as e:
                # Also covers a database damaged by being swapped out
                # mid-write ("database disk image is malformed").
                logger.exception("Cannot use the OAuth database")
                raise StoreUnavailableError(_UNAVAILABLE) from e
    except BackendUnavailableError as e:
        raise StoreUnavailableError(_UNAVAILABLE) from e
