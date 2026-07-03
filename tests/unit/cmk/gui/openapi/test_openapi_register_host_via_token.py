#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Endpoint tests for host registration via a one-time agent registration token.

The token has two independent one-time uses (host registration and agent updater
registration). This endpoint consumes the host registration use; the token is only
revoked once both uses are consumed.
"""

import datetime as dt
from uuid import uuid4

import pytest
from dateutil.relativedelta import relativedelta

from cmk.ccc.hostaddress import HostName
from cmk.ccc.user import UserId
from cmk.gui.token_auth import AgentRegistrationToken, AuthToken, get_token_store
from cmk.gui.token_auth._store import TokenRevoked
from tests.testlib.unit.rest_api_client import ClientRegistry


def _issue_token(host_name: str) -> AuthToken:
    return get_token_store().issue(
        token_details=AgentRegistrationToken(host_name=HostName(host_name)),
        issuer=UserId("issuer"),
        now=dt.datetime.now(dt.UTC),
        valid_for=relativedelta(days=1),
    )


@pytest.mark.usefixtures("with_host")
class TestRegisterHostViaToken:
    def test_success_consumes_host_registration_use(self, clients: ClientRegistry) -> None:
        token = _issue_token("heute")

        resp = clients.HostConfig.register_via_token("heute", f"0:{token.token_id}", str(uuid4()))

        resp.assert_status_code(200)
        stored = get_token_store().verify(f"0:{token.token_id}", now=dt.datetime.now(dt.UTC))
        assert isinstance(stored.details, AgentRegistrationToken)
        assert stored.details.host_registration_completed_at is not None
        assert stored.details.updater_registration_completed_at is None
        assert not stored.revoked
        # The remaining (updater registration) use is only valid for a grace period
        assert stored.valid_until is not None
        assert stored.valid_until <= dt.datetime.now(dt.UTC) + dt.timedelta(minutes=10)

    def test_second_host_registration_is_rejected(self, clients: ClientRegistry) -> None:
        token = _issue_token("heute")
        clients.HostConfig.register_via_token("heute", f"0:{token.token_id}", str(uuid4()))

        resp = clients.HostConfig.register_via_token(
            "heute", f"0:{token.token_id}", str(uuid4()), expect_ok=False
        )

        resp.assert_status_code(403)
        assert resp.json["title"] == "Token already used"

    def test_both_uses_consumed_revokes_token(self, clients: ClientRegistry) -> None:
        token = _issue_token("heute")
        get_token_store().consume_agent_registration_use(
            token.token_id, "updater_registration", dt.datetime.now(dt.UTC)
        )

        resp = clients.HostConfig.register_via_token("heute", f"0:{token.token_id}", str(uuid4()))

        resp.assert_status_code(200)
        with pytest.raises(TokenRevoked):
            get_token_store().verify(f"0:{token.token_id}", now=dt.datetime.now(dt.UTC))

    def test_revoked_token_is_rejected(self, clients: ClientRegistry) -> None:
        token = _issue_token("heute")
        get_token_store().revoke(token.token_id)

        resp = clients.HostConfig.register_via_token(
            "heute", f"0:{token.token_id}", str(uuid4()), expect_ok=False
        )

        resp.assert_status_code(401)

    def test_token_for_different_host_is_rejected(self, clients: ClientRegistry) -> None:
        token = _issue_token("other_host")

        resp = clients.HostConfig.register_via_token(
            "heute", f"0:{token.token_id}", str(uuid4()), expect_ok=False
        )

        resp.assert_status_code(403)
        assert "different host" in resp.json["detail"]
