#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime as dt
from pathlib import Path

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.ccc.user import UserId
from cmk.gui.token_auth import (
    AgentDownloadToken,
    AgentRegistrationToken,
    get_token_store,
)
from cmk.gui.watolib.agent_token_automations import (
    AgentDownloadTokenCreateRequest,
    AgentRegistrationTokenCreateRequest,
    AutomationAgentDownloadTokenCreate,
    AutomationAgentRegistrationTokenCreate,
    TokenCreateResponse,
)
from cmk.utils import paths
from cmk.utils.agent_registration import HostAgentConnectionMode


@pytest.fixture
def isolated_token_store(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setattr(paths, "var_dir", tmp_path)
    return tmp_path / "token.store"


class TestAutomationAgentDownloadTokenCreate:
    def test_issues_token_in_local_store(self, isolated_token_store: Path) -> None:
        expires_at = dt.datetime(2030, 1, 1, tzinfo=dt.UTC)
        api_request = AgentDownloadTokenCreateRequest(issuer=UserId("admin"), expires_at=expires_at)

        result = TokenCreateResponse.model_validate(
            AutomationAgentDownloadTokenCreate().execute(api_request)
        )

        stored = get_token_store().verify(f"0:{result.id}", now=dt.datetime.now(dt.UTC))
        assert isinstance(stored.details, AgentDownloadToken)
        assert stored.issuer == UserId("admin")
        assert stored.valid_until == expires_at
        assert result.expires_at == expires_at

    def test_no_expiration_yields_token_without_expiry(self, isolated_token_store: Path) -> None:
        api_request = AgentDownloadTokenCreateRequest(issuer=UserId("admin"), expires_at=None)

        result = TokenCreateResponse.model_validate(
            AutomationAgentDownloadTokenCreate().execute(api_request)
        )

        assert result.expires_at is None
        stored = get_token_store().verify(f"0:{result.id}", now=dt.datetime.now(dt.UTC))
        assert stored.valid_until is None


class TestAutomationAgentRegistrationTokenCreate:
    def test_issues_token_with_host_name_and_comment(self, isolated_token_store: Path) -> None:
        expires_at = dt.datetime(2030, 1, 1, tzinfo=dt.UTC)
        api_request = AgentRegistrationTokenCreateRequest(
            issuer=UserId("admin"),
            host_name=HostName("my-host"),
            connection_mode=HostAgentConnectionMode.PULL,
            expires_at=expires_at,
            comment="from slideout",
        )

        result = TokenCreateResponse.model_validate(
            AutomationAgentRegistrationTokenCreate().execute(api_request)
        )

        stored = get_token_store().verify(f"0:{result.id}", now=dt.datetime.now(dt.UTC))
        assert isinstance(stored.details, AgentRegistrationToken)
        assert stored.details.host_name == HostName("my-host")
        assert stored.details.comment == "from slideout"
        assert stored.details.connection_mode is HostAgentConnectionMode.PULL
        assert stored.issuer == UserId("admin")
        assert stored.valid_until == expires_at

    def test_push_mode_is_persisted_in_token(self, isolated_token_store: Path) -> None:
        api_request = AgentRegistrationTokenCreateRequest(
            issuer=UserId("admin"),
            host_name=HostName("push-host"),
            connection_mode=HostAgentConnectionMode.PUSH,
        )

        result = TokenCreateResponse.model_validate(
            AutomationAgentRegistrationTokenCreate().execute(api_request)
        )

        stored = get_token_store().verify(f"0:{result.id}", now=dt.datetime.now(dt.UTC))
        assert isinstance(stored.details, AgentRegistrationToken)
        assert stored.details.connection_mode is HostAgentConnectionMode.PUSH


class TestRequestModelValidation:
    def test_download_request_rejects_invalid_user_id(self) -> None:
        with pytest.raises(ValueError, match="invalid username"):
            AgentDownloadTokenCreateRequest.model_validate(
                {"issuer": "not a valid user!", "expires_at": None}
            )

    def test_registration_request_rejects_invalid_host_name(self) -> None:
        with pytest.raises(ValueError):
            AgentRegistrationTokenCreateRequest.model_validate(
                {
                    "issuer": "admin",
                    "host_name": "invalid host name",
                    "connection_mode": "pull-agent",
                    "comment": "",
                }
            )


class TestTokenCreateResponse:
    def test_roundtrips_via_json(self) -> None:
        original = TokenCreateResponse(
            id="abc-123",
            issued_at=dt.datetime(2026, 4, 27, 10, 0, tzinfo=dt.UTC),
            expires_at=dt.datetime(2026, 5, 4, 10, 0, tzinfo=dt.UTC),
        )
        roundtrip = TokenCreateResponse.model_validate(original.model_dump(mode="json"))
        assert roundtrip == original

    def test_accepts_no_expiry(self) -> None:
        parsed = TokenCreateResponse.model_validate(
            {
                "id": "abc-123",
                "issued_at": "2026-04-27T10:00:00+00:00",
                "expires_at": None,
            }
        )
        assert parsed.expires_at is None
