#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime as dt
from collections.abc import Iterator
from contextlib import contextmanager
from typing import cast
from unittest.mock import MagicMock

import pytest

from cmk.ccc.user import UserId
from cmk.gui.dashboard.api import _widget_resolution as resolution_module
from cmk.gui.dashboard.token_util import InvalidWidgetError
from cmk.gui.dashboard.type_defs import DashboardConfig, DashletConfig
from cmk.gui.openapi.framework import ApiContext
from cmk.gui.session_context import UserContext
from cmk.gui.token_auth import AuthToken, DashboardToken, TokenId
from cmk.gui.type_defs import VisualContext
from cmk.gui.utils.roles import UserPermissions

ISSUER = UserId("cmkadmin")
TOKEN_ID = TokenId("the-token")
WIDGET_ID = "test_dashboard-0"


def dashboard_token(*, disabled: bool = False, issuer: UserId = ISSUER) -> AuthToken:
    return AuthToken(
        issuer=issuer,
        issued_at=dt.datetime(2026, 1, 1, tzinfo=dt.UTC),
        valid_until=None,
        token_id=TOKEN_ID,
        details=DashboardToken(
            owner=issuer,
            dashboard_name="test_dashboard",
            disabled=disabled,
            synced_at=dt.datetime(2026, 1, 1, tzinfo=dt.UTC),
        ),
    )


def api_context(
    token: AuthToken | None,
    user_permissions: UserPermissions | None = None,
    *,
    default_temperature_unit: str = "celsius",
) -> ApiContext:
    context = MagicMock(spec=ApiContext)
    context.token = token
    context.config.debug = False
    context.config.default_temperature_unit = default_temperature_unit
    context.config.user_permissions.return_value = user_permissions or UserPermissions(
        {}, {}, {}, []
    )
    return context


def dashboard_widget(
    widget_type: str = "hoststats", context: VisualContext | None = None, **extra: object
) -> DashletConfig:
    return cast(
        DashletConfig,
        {"type": widget_type, "context": context or {}, "single_infos": [], **extra},
    )


def impersonating(
    monkeypatch: pytest.MonkeyPatch,
    widgets: dict[str, DashletConfig],
    *,
    issuer: UserId = ISSUER,
    dashboard_context: VisualContext | None = None,
) -> None:
    board = cast(
        DashboardConfig,
        {
            "name": "test_dashboard",
            "owner": issuer,
            "context": dashboard_context or {},
            "widgets": widgets,
        },
    )

    @contextmanager
    def _impersonate(
        issuer: UserId, _details: object, permissions: UserPermissions
    ) -> Iterator[MagicMock]:
        with UserContext(issuer, permissions):
            loaded = MagicMock()
            loaded.load_dashboard.return_value = board
            yield loaded

    monkeypatch.setattr(resolution_module, "impersonate_dashboard_token_issuer", _impersonate)


def impersonating_but_unpermitted(monkeypatch: pytest.MonkeyPatch) -> None:
    @contextmanager
    def _impersonate(
        issuer: UserId, _details: object, permissions: UserPermissions
    ) -> Iterator[MagicMock]:
        with UserContext(issuer, permissions):
            loaded = MagicMock()
            loaded.load_dashboard.side_effect = InvalidWidgetError(disable_token=True)
            yield loaded

    monkeypatch.setattr(resolution_module, "impersonate_dashboard_token_issuer", _impersonate)


def recording_token_retirement(monkeypatch: pytest.MonkeyPatch) -> list[TokenId]:
    disabled: list[TokenId] = []
    monkeypatch.setattr(resolution_module, "disable_dashboard_token_by_id", disabled.append)
    return disabled
