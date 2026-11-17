#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from html.parser import HTMLParser
from http import HTTPStatus
from typing import override

import pytest

from cmk.gui.dashboard.page_show_dashboard import shareable_contact_groups
from cmk.gui.groups import GroupSpecs
from tests.testlib.unit.gui.web_test_app import WebTestAppForCMK

_CONTACT_GROUPS: GroupSpecs = {
    "own": {"alias": "Own group"},
    "foreign": {"alias": "Foreign group"},
}


class _ComponentData(HTMLParser):
    def __init__(self, component: str) -> None:
        super().__init__()
        self._component = component
        self.data: dict[str, object] | None = None

    @override
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == self._component and (data := dict(attrs).get("data")) is not None:
            self.data = json.loads(data)


def _dashboard_app_data(app: WebTestAppForCMK, query: str) -> dict[str, object]:
    response = app.get(f"/NO_SITE/check_mk/dashboard.py?{query}", status=HTTPStatus.OK)
    parser = _ComponentData("cmk-dashboard")
    parser.feed(response.text)
    assert parser.data is not None, "The page holds no dashboard app"
    return parser.data


@pytest.mark.usefixtures("suppress_license_expiry_header", "patch_theme", "suppress_license_banner")
def test_a_dashboard_a_drill_down_opened_offers_the_way_back(
    logged_in_admin_wsgi_app: WebTestAppForCMK,
) -> None:
    data = _dashboard_app_data(logged_in_admin_wsgi_app, "name=main&_drilled_from=Overview")

    assert data["drill_up"] == {"title": "Overview"}


@pytest.mark.usefixtures("suppress_license_expiry_header", "patch_theme", "suppress_license_banner")
def test_a_dashboard_no_drill_down_opened_offers_no_way_back(
    logged_in_admin_wsgi_app: WebTestAppForCMK,
) -> None:
    data = _dashboard_app_data(logged_in_admin_wsgi_app, "name=main")

    assert data["drill_up"] is None


def test_shareable_contact_groups_without_publish_permission_are_empty() -> None:
    groups = shareable_contact_groups(
        _CONTACT_GROUPS, ["own"], may_share_with_own=False, may_share_with_foreign=False
    )

    assert groups == []


def test_shareable_contact_groups_with_own_permission_are_the_users_groups() -> None:
    groups = shareable_contact_groups(
        _CONTACT_GROUPS, ["own"], may_share_with_own=True, may_share_with_foreign=False
    )

    assert groups == [{"name": "own", "title": "Own group"}]


def test_shareable_contact_groups_with_foreign_permission_are_all_groups() -> None:
    groups = shareable_contact_groups(
        _CONTACT_GROUPS, ["own"], may_share_with_own=False, may_share_with_foreign=True
    )

    assert groups == [
        {"name": "own", "title": "Own group"},
        {"name": "foreign", "title": "Foreign group"},
    ]


def test_shareable_contact_groups_without_alias_are_titled_by_name() -> None:
    groups = shareable_contact_groups(
        {"own": {}}, ["own"], may_share_with_own=True, may_share_with_foreign=False
    )

    assert groups == [{"name": "own", "title": "own"}]
