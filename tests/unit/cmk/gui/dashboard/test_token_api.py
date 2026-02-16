#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime as dt
from collections.abc import Generator

import pytest

from cmk.ccc.user import UserId
from cmk.gui.token_auth import get_token_store, TokenId
from tests.testlib.common.repo import is_non_free_repo
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


@pytest.fixture(name="user_dashboard_with_token")
def fixture_user_dashboard_with_token(
    clients: ClientRegistry,
    with_automation_user: tuple[UserId, str],
    user_dashboard: str,
) -> Generator[str]:
    """Creates a user dashboard with a token for testing."""
    expires_at = (dt.datetime.now(dt.UTC) + dt.timedelta(days=1)).isoformat()
    payload = {
        "dashboard_owner": with_automation_user[0],
        "dashboard_id": user_dashboard,
        "comment": "User dashboard token",
        "expires_at": expires_at,
    }
    clients.DashboardClient.create_dashboard_token(payload)
    yield user_dashboard
    # Cleanup is handled by the user_dashboard fixture.


def test_create_token_builtin_dashboard(clients: ClientRegistry) -> None:
    expires_at = (dt.datetime.now(dt.UTC) + dt.timedelta(days=1)).isoformat()
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
    expires_at = (dt.datetime.now(dt.UTC) + dt.timedelta(days=1)).isoformat()
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


def test_create_token_expiration_in_past(
    clients: ClientRegistry,
    with_automation_user: tuple[UserId, str],
    user_dashboard: str,
) -> None:
    payload = {
        "dashboard_owner": with_automation_user[0],
        "dashboard_id": user_dashboard,
        "comment": "Invalid expiration",
        "expires_at": (dt.datetime.now(dt.UTC) - dt.timedelta(days=1)).isoformat(),
    }
    resp = clients.DashboardClient.create_dashboard_token(payload, expect_ok=False)
    assert resp.status_code == 400, f"Expected 400, got {resp.status_code} {resp.json!r}"
    assert resp.json["fields"]["body.expires_at"]["msg"] == "Input should be in the future"


def test_create_token_expiration_too_far_in_future(
    clients: ClientRegistry,
    with_automation_user: tuple[UserId, str],
    user_dashboard: str,
) -> None:
    if is_non_free_repo():
        pytest.skip("This test is only relevant for Checkmk Community Edition")

    payload = {
        "dashboard_owner": with_automation_user[0],
        "dashboard_id": user_dashboard,
        "comment": "Invalid expiration",
        "expires_at": (dt.datetime.now(dt.UTC) + dt.timedelta(days=800)).isoformat(),
    }
    resp = clients.DashboardClient.create_dashboard_token(payload, expect_ok=False)
    assert resp.status_code == 400, f"Expected 400, got {resp.status_code} {resp.json!r}"
    assert resp.json["fields"]["body.expires_at"]["msg"] == (
        "In Checkmk Community, dashboard tokens can only be valid for up to one month."
    )


def test_create_token_no_expiration(
    clients: ClientRegistry,
    with_automation_user: tuple[UserId, str],
    user_dashboard: str,
) -> None:
    if not is_non_free_repo():
        pytest.skip("This test is only relevant for commercial Checkmk editions")

    payload = {
        "dashboard_owner": with_automation_user[0],
        "dashboard_id": user_dashboard,
        "comment": "Invalid expiration",
        "expires_at": None,
    }
    resp = clients.DashboardClient.create_dashboard_token(payload)
    assert resp.status_code == 201, f"Expected 201, got {resp.status_code} {resp.json!r}"


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


def test_edit_token_user_dashboard(
    clients: ClientRegistry,
    with_automation_user: tuple[UserId, str],
    user_dashboard_with_token: str,
) -> None:
    new_expires = (
        (dt.datetime.now(dt.UTC) + dt.timedelta(days=2)).isoformat().replace("+00:00", "Z")
    )
    edit_payload = {
        "dashboard_owner": with_automation_user[0],
        "dashboard_id": user_dashboard_with_token,
        "comment": "Edited",
        "is_disabled": True,
        "expires_at": new_expires,
    }
    resp = clients.DashboardClient.edit_dashboard_token(edit_payload)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code} {resp.json!r}"
    assert resp.json["extensions"]["comment"] == "Edited"
    assert resp.json["extensions"]["is_disabled"] is True
    assert resp.json["extensions"]["expires_at"] == new_expires


def test_edit_token_builtin_dashboard(clients: ClientRegistry) -> None:
    edit_payload = {
        "dashboard_owner": "",
        "dashboard_id": "main",
        "comment": "Should fail",
        "is_disabled": True,
        "expires_at": (dt.datetime.now(dt.UTC) + dt.timedelta(days=1)).isoformat(),
    }
    resp = clients.DashboardClient.edit_dashboard_token(edit_payload, expect_ok=False)
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code} {resp.json!r}"
    assert (
        resp.json["detail"] == "You are not allowed to edit dashboards owned by the built-in user."
    )


def test_edit_token_expiration_in_past(
    clients: ClientRegistry,
    with_automation_user: tuple[UserId, str],
    user_dashboard: str,
) -> None:
    create_payload = {
        "dashboard_owner": with_automation_user[0],
        "dashboard_id": user_dashboard,
        "comment": "Initial",
    }
    clients.DashboardClient.create_dashboard_token(create_payload)
    edit_payload = {
        "dashboard_owner": with_automation_user[0],
        "dashboard_id": user_dashboard,
        "comment": "Edited",
        "is_disabled": False,
        "expires_at": (dt.datetime.now(dt.UTC) - dt.timedelta(days=1)).isoformat(),
    }
    resp = clients.DashboardClient.edit_dashboard_token(edit_payload)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code} {resp.json!r}"


def test_edit_token_invalid_expiration(
    clients: ClientRegistry,
    with_automation_user: tuple[UserId, str],
    user_dashboard_with_token: str,
) -> None:
    if is_non_free_repo():
        pytest.skip("This test is only relevant for Checkmk Community Edition")

    edit_payload = {
        "dashboard_owner": with_automation_user[0],
        "dashboard_id": user_dashboard_with_token,
        "comment": "Edited",
        "is_disabled": False,
        "expires_at": (dt.datetime.now(dt.UTC) + dt.timedelta(days=800)).isoformat(),
    }
    resp = clients.DashboardClient.edit_dashboard_token(edit_payload, expect_ok=False)
    assert resp.status_code == 400, f"Expected 400, got {resp.status_code} {resp.json!r}"
    assert resp.json["fields"]["body.expires_at"]["msg"] == (
        "In Checkmk Community, dashboard tokens can only be valid for up to one month."
    )


def test_edit_token_no_expiration(
    clients: ClientRegistry,
    with_automation_user: tuple[UserId, str],
    user_dashboard_with_token: str,
) -> None:
    if not is_non_free_repo():
        pytest.skip("This test is only relevant for commercial Checkmk editions")

    edit_payload = {
        "dashboard_owner": with_automation_user[0],
        "dashboard_id": user_dashboard_with_token,
        "comment": "Edited",
        "is_disabled": False,
        "expires_at": None,
    }
    resp = clients.DashboardClient.edit_dashboard_token(edit_payload)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code} {resp.json!r}"


def test_edit_token_nonexistent_dashboard(
    clients: ClientRegistry, with_automation_user: tuple[UserId, str]
) -> None:
    edit_payload = {
        "dashboard_owner": with_automation_user[0],
        "dashboard_id": "does_not_exist",
        "comment": "Should fail",
        "is_disabled": True,
        "expires_at": (dt.datetime.now(dt.UTC) + dt.timedelta(days=1)).isoformat(),
    }
    resp = clients.DashboardClient.edit_dashboard_token(edit_payload, expect_ok=False)
    assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
    assert resp.json["title"] == "Dashboard not found"


def test_delete_token_user_dashboard(
    clients: ClientRegistry,
    with_automation_user: tuple[UserId, str],
    user_dashboard_with_token: str,
) -> None:
    delete_payload = {
        "dashboard_owner": with_automation_user[0],
        "dashboard_id": user_dashboard_with_token,
    }
    resp = clients.DashboardClient.delete_dashboard_token(delete_payload)
    assert resp.status_code == 204, f"Expected 204, got {resp.status_code}"


def test_delete_token_builtin_dashboard(clients: ClientRegistry) -> None:
    delete_payload = {
        "dashboard_owner": "",
        "dashboard_id": "main",
    }
    resp = clients.DashboardClient.delete_dashboard_token(delete_payload, expect_ok=False)
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code} {resp.json!r}"
    assert (
        resp.json["detail"] == "You are not allowed to edit dashboards owned by the built-in user."
    )


def test_delete_token_nonexistent_dashboard(
    clients: ClientRegistry, with_automation_user: tuple[UserId, str]
) -> None:
    delete_payload = {
        "dashboard_owner": with_automation_user[0],
        "dashboard_id": "does_not_exist",
    }
    resp = clients.DashboardClient.delete_dashboard_token(delete_payload, expect_ok=False)
    assert resp.status_code == 404, f"Expected 404, got {resp.status_code} {resp.json!r}"
    assert resp.json["title"] == "Dashboard not found"


def test_delete_token_no_token(
    clients: ClientRegistry, with_automation_user: tuple[UserId, str], user_dashboard: str
) -> None:
    delete_payload = {
        "dashboard_owner": with_automation_user[0],
        "dashboard_id": user_dashboard,
    }
    resp = clients.DashboardClient.delete_dashboard_token(delete_payload, expect_ok=False)
    assert resp.status_code == 404, f"Expected 404, got {resp.status_code} {resp.json!r}"
    assert resp.json["title"] == "Dashboard token not found"


def test_get_token_user_dashboard(
    clients: ClientRegistry,
    with_automation_user: tuple[UserId, str],
    user_dashboard_with_token: str,
) -> None:
    resp = clients.DashboardClient.get_relative_grid_dashboard(user_dashboard_with_token)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code} {resp.json!r}"
    assert resp.json["extensions"]["public_token"]["token_id"] is not None


def test_create_token_with_stale_reference(
    clients: ClientRegistry,
    with_automation_user: tuple[UserId, str],
    user_dashboard_with_token: str,
) -> None:
    """Regression test: creating a token should succeed when the dashboard config
    references a token that no longer exists in the token store (stale reference)."""
    resp = clients.DashboardClient.get_relative_grid_dashboard(user_dashboard_with_token)
    assert resp.status_code == 200
    token_id = resp.json["extensions"]["public_token"]["token_id"]

    # Simulate a stale token reference by deleting the token directly from the token store
    token_store = get_token_store()
    token_store.delete(TokenId(token_id))

    payload = {
        "dashboard_owner": with_automation_user[0],
        "dashboard_id": user_dashboard_with_token,
        "comment": "Re-created after stale reference",
        "expires_at": (dt.datetime.now(dt.UTC) + dt.timedelta(days=1)).isoformat(),
    }
    resp = clients.DashboardClient.create_dashboard_token(payload)
    assert resp.status_code == 201, f"Expected 201, got {resp.status_code} {resp.json!r}"
    assert resp.json["id"] is not None
