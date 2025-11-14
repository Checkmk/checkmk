#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime as dt
from collections.abc import Generator

import pytest

from cmk.ccc.user import UserId
from tests.testlib.unit.rest_api_client import ClientRegistry


@pytest.fixture(name="user_dashboard")
def fixture_user_dashboard(clients: ClientRegistry, with_automation_user: str) -> Generator[str]:
    """Creates an empty user dashboard for testing, using the automation user."""
    user_dashboard_id = "user_test_dashboard"
    payload = {
        "id": user_dashboard_id,
        "general_settings": {
            "title": {"text": "User Test Dashboard", "render": True, "include_context": False},
            "description": "Test user dashboard for token API",
            "menu": {
                "topic": "overview",
                "sort_index": 99,
                "search_terms": [],
                "is_show_more": False,
            },
            "visibility": {
                "hide_in_monitor_menu": False,
                "hide_in_drop_down_menus": False,
                "share": "no",
            },
        },
        "filter_context": {
            "restricted_to_single": [],
            "filters": {},
            "mandatory_context_filters": [],
        },
        "widgets": {},
        "layout": {"type": "relative_grid"},
    }
    clients.DashboardClient.create_relative_grid_dashboard(payload)
    yield user_dashboard_id
    clients.DashboardClient.delete(user_dashboard_id)


def test_create_token_builtin_dashboard(clients: ClientRegistry) -> None:
    expires_at = (dt.datetime.now(dt.UTC) + dt.timedelta(days=30)).isoformat()
    payload = {
        "dashboard_owner": "",
        "dashboard_id": "main",
        "comment": "Should fail",
        "expires_at": expires_at,
    }
    resp = clients.DashboardClient.create_dashboard_token(payload, expect_ok=False)
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code} {resp.json!r}"
    assert (
        resp.json["detail"] == "You are not allowed to edit dashboards owned by the built-in user."
    )


def test_create_token_user_dashboard(
    clients: ClientRegistry, with_automation_user: tuple[UserId, str], user_dashboard: str
) -> None:
    expires_at = (dt.datetime.now(dt.UTC) + dt.timedelta(days=30)).isoformat()
    payload = {
        "dashboard_owner": with_automation_user[0],
        "dashboard_id": user_dashboard,
        "comment": "User dashboard token",
        "expires_at": expires_at,
    }
    resp = clients.DashboardClient.create_dashboard_token(payload)
    assert resp.status_code == 201, f"Expected 201, got {resp.status_code} {resp.json!r}"
    assert resp.json["id"] is not None
    assert resp.json["extensions"]["comment"] == "User dashboard token"
    assert resp.json["extensions"]["expires_at"] == expires_at.replace("+00:00", "Z")
    assert resp.json["extensions"]["is_disabled"] is False
    assert resp.json["extensions"]["issued_at"] is not None


@pytest.mark.parametrize(
    "expires_at, expected_error",
    [
        pytest.param(
            (dt.datetime.now(dt.UTC) - dt.timedelta(days=1)).isoformat(),
            "Input should be in the future",
            id="expiration_in_past",
        ),
        pytest.param(
            (dt.datetime.now(dt.UTC) + dt.timedelta(days=800)).isoformat(),
            "Value error, Expiration time must be less than two years from now.",
            id="expiration_too_far_in_future",
        ),
    ],
)
def test_create_token_invalid_expiration(
    clients: ClientRegistry,
    with_automation_user: tuple[UserId, str],
    user_dashboard: str,
    expires_at: str,
    expected_error: str,
) -> None:
    payload = {
        "dashboard_owner": with_automation_user[0],
        "dashboard_id": user_dashboard,
        "comment": "Invalid expiration",
        "expires_at": expires_at,
    }
    resp = clients.DashboardClient.create_dashboard_token(payload, expect_ok=False)
    assert resp.status_code == 400, f"Expected 400, got {resp.status_code} {resp.json!r}"
    assert resp.json["fields"]["body.expires_at"]["msg"] == expected_error


def test_create_token_nonexistent_dashboard(
    clients: ClientRegistry, with_automation_user: tuple[UserId, str]
) -> None:
    payload = {
        "dashboard_owner": with_automation_user[0],
        "dashboard_id": "does_not_exist",
        "comment": "Should fail",
    }
    resp = clients.DashboardClient.create_dashboard_token(payload, expect_ok=False)
    assert resp.status_code == 404, f"Expected 404, got {resp.status_code} {resp.json!r}"
    assert resp.json["title"] == "Dashboard not found"
