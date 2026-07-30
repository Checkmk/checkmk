#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""A damaged OAuth database is answered, not crashed on.

The end-to-end version of what test_backend.py already checks at the
connect() level: a request against an unusable database is refused as
unauthenticated rather than reaching the unhandled-exception path.
"""

from datetime import datetime, timedelta, UTC

from cmk.ccc.user import UserId
from cmk.gui.oauth.store.backend import oauth_db_path
from cmk.gui.oauth.store.client_store import get_client_store
from cmk.gui.oauth.store.token_store import get_token_store
from cmk.gui.scopes import DEFAULT_SCOPE
from tests.unit.cmk.web_test_app import WebTestAppForCMK


def test_a_damaged_database_does_not_authenticate_anyone(
    wsgi_app: WebTestAppForCMK, with_user: tuple[UserId, str]
) -> None:
    """A token this site cannot check is answered, not crashed on.

    The request is refused as unauthenticated rather than reaching the
    unhandled-exception path, which would cost a crash report per request.
    """
    username, _password = with_user
    with get_client_store() as clients:
        registration = clients.register(["https://client.example/callback"], None)
    assert registration.is_ok()
    with get_token_store() as tokens:
        token = tokens.issue_token(
            username,
            expires_at=datetime.now(UTC) + timedelta(minutes=5),
            resource=None,
            scope=DEFAULT_SCOPE,
            client_id=registration.ok.client_id,
        )
    assert token.is_ok()
    with oauth_db_path().open("r+b") as database:
        # Overwrite the first page, as an interrupted copy would leave it.
        database.seek(100)
        database.write(b"\x00" * 4096)

    response = wsgi_app.get(
        "/NO_SITE/check_mk/api/1.0/version",
        headers={"Accept": "application/json", "Authorization": f"Bearer {token.ok}"},
        status=401,
    )

    # The database path and the sqlite error stay in the log: this response
    # also goes to callers that are not authenticated.
    assert "sqlite" not in response.text
