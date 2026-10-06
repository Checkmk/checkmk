#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime as dt
from http import HTTPStatus
from pathlib import Path

import pytest
from dateutil.relativedelta import relativedelta

from cmk.ccc.user import UserId
from cmk.gui.agent_download import (
    AgentPackageUnavailable,
    DOWNLOAD_TOKEN_FAILURE_DETAIL,
    OneTimeDownloadToken,
)
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.token_auth import AgentDownloadToken, AuthToken, InvalidToken, TokenId, TokenStore

_NOW = dt.datetime(2026, 10, 6, tzinfo=dt.UTC)


def _issue(store: TokenStore) -> AuthToken:
    return store.issue(
        token_details=AgentDownloadToken(),
        issuer=UserId("issuer"),
        now=_NOW,
        valid_for=relativedelta(days=1),
    )


def test_download_uses_up_the_token(tmp_path: Path) -> None:
    store = TokenStore(tmp_path / "token.store")
    token = _issue(store)

    with OneTimeDownloadToken(token.token_id, store):
        pass

    with pytest.raises(InvalidToken):
        store.verify(f"0:{token.token_id}", now=_NOW)


def test_unavailable_package_keeps_the_token(tmp_path: Path) -> None:
    store = TokenStore(tmp_path / "token.store")
    token = _issue(store)

    with (
        pytest.raises(AgentPackageUnavailable),
        OneTimeDownloadToken(token.token_id, store),
    ):
        raise AgentPackageUnavailable(status=HTTPStatus.NOT_FOUND)

    assert store.verify(f"0:{token.token_id}", now=_NOW).token_id == token.token_id


def test_other_download_failure_uses_up_the_token(tmp_path: Path) -> None:
    store = TokenStore(tmp_path / "token.store")
    token = _issue(store)

    with (
        pytest.raises(ProblemException),
        OneTimeDownloadToken(token.token_id, store),
    ):
        raise ProblemException(status=HTTPStatus.UNPROCESSABLE_ENTITY)

    with pytest.raises(InvalidToken):
        store.verify(f"0:{token.token_id}", now=_NOW)


def test_token_gone_from_the_store_is_unauthorized(tmp_path: Path) -> None:
    store = TokenStore(tmp_path / "token.store")

    with pytest.raises(ProblemException) as exc_info, OneTimeDownloadToken(TokenId("gone"), store):
        pass

    assert exc_info.value.code == HTTPStatus.UNAUTHORIZED
    assert exc_info.value.detail == DOWNLOAD_TOKEN_FAILURE_DETAIL
