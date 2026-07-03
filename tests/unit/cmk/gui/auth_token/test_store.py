#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
import json
from pathlib import Path

import pytest
from dateutil.relativedelta import relativedelta

from cmk.ccc.hostaddress import HostName
from cmk.ccc.user import UserId
from cmk.gui.token_auth import AgentRegistrationToken, DashboardToken, TokenId, TokenStore
from cmk.gui.token_auth._store import (
    AGENT_REGISTRATION_TOKEN_GRACE_PERIOD,
    AgentRegistrationUse,
    AuthToken,
    InvalidToken,
    TokenExpired,
    TokenRevoked,
    TokenTypeError,
    TokenUseAlreadyConsumed,
)
from cmk.utils.agent_registration import HostAgentConnectionMode

some_time = datetime.datetime(2020, 1, 20, 20, 20, 20, tzinfo=datetime.UTC)


def test_successful_verification(tmp_path: Path) -> None:
    store = TokenStore(tmp_path / "store.json")
    token = store.issue(
        token_details=DashboardToken(
            owner=UserId("owner"),
            dashboard_name="unit-dashboard",
            synced_at=some_time,
        ),
        issuer=UserId("issuer"),
        now=some_time,
        valid_for=relativedelta(days=1),
    )
    store.verify(f"0:{token.token_id}", now=some_time)


def test_revokation(tmp_path: Path) -> None:
    store = TokenStore(tmp_path / "store.json")
    token = store.issue(
        token_details=DashboardToken(
            owner=UserId("owner"),
            dashboard_name="unit-dashboard",
            synced_at=some_time,
        ),
        issuer=UserId("issuer"),
        now=some_time,
        valid_for=relativedelta(days=1),
    )
    store.revoke(token.token_id)

    with pytest.raises(TokenRevoked):
        store.verify(f"0:{token.token_id}", now=some_time)


def test_expired_w_expiration(tmp_path: Path) -> None:
    store = TokenStore(tmp_path / "store.json")
    token = store.issue(
        token_details=DashboardToken(
            owner=UserId("owner"),
            dashboard_name="unit-dashboard",
            synced_at=some_time,
        ),
        issuer=UserId("issuer"),
        now=some_time,
        valid_for=relativedelta(days=1),
    )

    with pytest.raises(TokenExpired):
        store.verify(f"0:{token.token_id}", now=some_time + datetime.timedelta(days=1, seconds=1))


def test_expired_wo_expiration(tmp_path: Path) -> None:
    store = TokenStore(tmp_path / "store.json")
    token = store.issue(
        token_details=DashboardToken(
            owner=UserId("owner"),
            dashboard_name="unit-dashboard",
            synced_at=some_time,
        ),
        issuer=UserId("issuer"),
        now=some_time,
        valid_for=None,
    )
    store.verify(f"0:{token.token_id}", now=some_time + datetime.timedelta(days=1, seconds=1))


def test_invalid_token(tmp_path: Path) -> None:
    store = TokenStore(tmp_path / "store.json")

    with pytest.raises(InvalidToken, match="Could not parse token"):
        store.verify("invalid", now=some_time)

    with pytest.raises(InvalidToken, match="Invalid token version 'invalid'"):
        store.verify("invalid:also invalid", now=some_time)

    with pytest.raises(InvalidToken, match="Could not find token 'foo'"):
        store.verify("0:foo", now=some_time)


def test_issued_at(tmp_path: Path) -> None:
    store = TokenStore(tmp_path / "store.json")
    token = store.issue(
        token_details=DashboardToken(
            owner=UserId("owner"),
            dashboard_name="unit-dashboard",
            synced_at=some_time,
        ),
        issuer=UserId("issuer"),
        now=some_time,
        valid_for=relativedelta(days=1),
    )
    assert token.issued_at == some_time


def test_delete_token(tmp_path: Path) -> None:
    store = TokenStore(tmp_path / "store.json")
    token = store.issue(
        token_details=DashboardToken(
            owner=UserId("owner"),
            dashboard_name="unit-dashboard",
            synced_at=some_time,
        ),
        issuer=UserId("issuer"),
        now=some_time,
        valid_for=relativedelta(days=1),
    )

    store.delete(token.token_id)

    with pytest.raises(InvalidToken, match=f"Could not find token '{token.token_id}'"):
        store.verify(f"0:{token.token_id}", now=some_time)


def test_last_successful_verification(tmp_path: Path) -> None:
    store = TokenStore(tmp_path / "store.json")
    token = store.issue(
        token_details=DashboardToken(
            owner=UserId("owner"),
            dashboard_name="unit-dashboard",
            synced_at=some_time,
        ),
        issuer=UserId("issuer"),
        now=some_time,
        valid_for=relativedelta(days=1),
    )
    assert token.last_successful_verification is None

    token = store.verify(f"0:{token.token_id}", now=some_time)
    # It was never verified before
    assert token.last_successful_verification is None

    token = store.verify(f"0:{token.token_id}", now=some_time)
    assert token.last_successful_verification == some_time


def _issue_agent_registration_token(
    store: TokenStore, valid_for: relativedelta | None = relativedelta(days=1)
) -> AuthToken:
    return store.issue(
        token_details=AgentRegistrationToken(host_name=HostName("my-host")),
        issuer=UserId("issuer"),
        now=some_time,
        valid_for=valid_for,
    )


@pytest.mark.parametrize(
    "use,consumed_field,free_field",
    [
        pytest.param(
            "host_registration",
            "host_registration_completed_at",
            "updater_registration_completed_at",
            id="host registration",
        ),
        pytest.param(
            "updater_registration",
            "updater_registration_completed_at",
            "host_registration_completed_at",
            id="updater registration",
        ),
    ],
)
def test_consume_first_agent_registration_use(
    tmp_path: Path, use: AgentRegistrationUse, consumed_field: str, free_field: str
) -> None:
    store = TokenStore(tmp_path / "store.json")
    token = _issue_agent_registration_token(store)

    store.consume_agent_registration_use(token.token_id, use, some_time)

    token = store.verify(f"0:{token.token_id}", now=some_time)
    assert isinstance(token.details, AgentRegistrationToken)
    assert getattr(token.details, consumed_field) == some_time
    assert getattr(token.details, free_field) is None
    assert not token.revoked
    assert token.valid_until == some_time + AGENT_REGISTRATION_TOKEN_GRACE_PERIOD


@pytest.mark.parametrize(
    "first,second",
    [
        pytest.param("host_registration", "updater_registration", id="host first"),
        pytest.param("updater_registration", "host_registration", id="updater first"),
    ],
)
def test_consume_both_agent_registration_uses_revokes(
    tmp_path: Path, first: AgentRegistrationUse, second: AgentRegistrationUse
) -> None:
    store = TokenStore(tmp_path / "store.json")
    token = _issue_agent_registration_token(store)
    within_grace = some_time + AGENT_REGISTRATION_TOKEN_GRACE_PERIOD - datetime.timedelta(minutes=1)

    store.consume_agent_registration_use(token.token_id, first, some_time)
    store.consume_agent_registration_use(token.token_id, second, within_grace)

    with pytest.raises(TokenRevoked):
        store.verify(f"0:{token.token_id}", now=within_grace)


@pytest.mark.parametrize("use", ["host_registration", "updater_registration"])
def test_consume_same_agent_registration_use_twice(
    tmp_path: Path, use: AgentRegistrationUse
) -> None:
    store = TokenStore(tmp_path / "store.json")
    token = _issue_agent_registration_token(store)
    store.consume_agent_registration_use(token.token_id, use, some_time)

    with pytest.raises(TokenUseAlreadyConsumed):
        store.consume_agent_registration_use(token.token_id, use, some_time)

    # The failed consumption must not have changed anything
    token = store.verify(f"0:{token.token_id}", now=some_time)
    assert not token.revoked
    assert token.valid_until == some_time + AGENT_REGISTRATION_TOKEN_GRACE_PERIOD


def test_consume_agent_registration_use_wrong_token_type(tmp_path: Path) -> None:
    store = TokenStore(tmp_path / "store.json")
    token = store.issue(
        token_details=DashboardToken(
            owner=UserId("owner"),
            dashboard_name="unit-dashboard",
            synced_at=some_time,
        ),
        issuer=UserId("issuer"),
        now=some_time,
        valid_for=relativedelta(days=1),
    )

    with pytest.raises(TokenTypeError, match="not an agent registration token"):
        store.consume_agent_registration_use(token.token_id, "host_registration", some_time)


def test_consume_agent_registration_use_unknown_token(tmp_path: Path) -> None:
    store = TokenStore(tmp_path / "store.json")
    _issue_agent_registration_token(store)

    with pytest.raises(InvalidToken, match="Could not find token 'unknown'"):
        store.consume_agent_registration_use(TokenId("unknown"), "host_registration", some_time)


def test_consume_agent_registration_use_expires_token_after_grace_period(tmp_path: Path) -> None:
    store = TokenStore(tmp_path / "store.json")
    token = _issue_agent_registration_token(store, valid_for=relativedelta(days=1))

    store.consume_agent_registration_use(token.token_id, "host_registration", some_time)

    store.verify(
        f"0:{token.token_id}",
        now=some_time + AGENT_REGISTRATION_TOKEN_GRACE_PERIOD - datetime.timedelta(minutes=1),
    )
    with pytest.raises(TokenExpired):
        store.verify(
            f"0:{token.token_id}",
            now=some_time + AGENT_REGISTRATION_TOKEN_GRACE_PERIOD + datetime.timedelta(seconds=1),
        )


def test_consume_agent_registration_use_caps_unlimited_validity(tmp_path: Path) -> None:
    store = TokenStore(tmp_path / "store.json")
    token = _issue_agent_registration_token(store, valid_for=None)

    store.consume_agent_registration_use(token.token_id, "host_registration", some_time)

    token = store.verify(f"0:{token.token_id}", now=some_time)
    assert token.valid_until == some_time + AGENT_REGISTRATION_TOKEN_GRACE_PERIOD


def test_consume_agent_registration_use_does_not_extend_validity(tmp_path: Path) -> None:
    store = TokenStore(tmp_path / "store.json")
    token = _issue_agent_registration_token(store, valid_for=relativedelta(minutes=5))

    store.consume_agent_registration_use(token.token_id, "host_registration", some_time)

    token = store.verify(f"0:{token.token_id}", now=some_time)
    assert token.valid_until == some_time + datetime.timedelta(minutes=5)


def test_deserialize_agent_registration_token_without_usage_fields(tmp_path: Path) -> None:
    """Tokens persisted before the usage tracking was added must still deserialize"""
    path = tmp_path / "store.json"
    path.write_text(
        json.dumps(
            {
                "legacy-token": {
                    "issuer": "issuer",
                    "issued_at": "2020-01-20T20:20:20+00:00",
                    "valid_until": None,
                    "details": {
                        "type_": "agent_registration",
                        "host_name": "my-host",
                        "connection_mode": HostAgentConnectionMode.PULL.value,
                        "comment": "",
                    },
                    "token_id": "legacy-token",
                    "revoked": False,
                }
            }
        )
    )
    store = TokenStore(path)

    token = store.verify("0:legacy-token", now=some_time)

    assert isinstance(token.details, AgentRegistrationToken)
    assert token.details.host_registration_completed_at is None
    assert token.details.updater_registration_completed_at is None
