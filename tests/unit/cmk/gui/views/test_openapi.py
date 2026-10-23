#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from http import HTTPStatus

from cmk.ccc.user import UserId
from cmk.gui import visuals
from cmk.gui.views.store import multisite_builtin_views
from tests.testlib.unit.rest_api_client import ClientRegistry


def test_list_views(clients: ClientRegistry) -> None:
    resp = clients.ViewClient.get_all()
    assert resp.status_code == HTTPStatus.OK, f"Expected 200, got {resp.status_code} {resp.body!r}"
    assert len(resp.json["value"]) > 0, "Expected at least one view to be returned"


def test_list_views_reports_the_empty_owner_for_a_built_in_view(clients: ClientRegistry) -> None:
    views = {view["id"]: view for view in clients.ViewClient.get_all().json["value"]}

    assert views["allhosts"]["extensions"]["owner"] == ""


def _save_own_copy(user_id: UserId, view_name: str) -> None:
    # Written straight to the store: a views store built in the test would serve the request.
    copy = multisite_builtin_views[view_name].copy()
    copy["owner"] = user_id
    visuals.save("views", {(user_id, view_name): copy}, user_id)


def test_list_views_offers_only_the_own_copy_of_a_customised_view(
    clients: ClientRegistry, with_automation_user: tuple[UserId, str]
) -> None:
    _save_own_copy(with_automation_user[0], "allhosts")

    views = clients.ViewClient.get_all().json["value"]

    assert [view["extensions"]["owner"] for view in views if view["id"] == "allhosts"] == [
        with_automation_user[0]
    ]


def test_list_views_with_all_owners_offers_the_built_in_beside_the_own_copy(
    clients: ClientRegistry, with_automation_user: tuple[UserId, str]
) -> None:
    _save_own_copy(with_automation_user[0], "allhosts")

    views = clients.ViewClient.get_all(all_owners=True).json["value"]

    assert sorted(
        view["extensions"]["owner"] for view in views if view["id"] == "allhosts"
    ) == sorted(["", with_automation_user[0]])
