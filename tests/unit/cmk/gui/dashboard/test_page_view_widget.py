#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from http import HTTPStatus

import pytest

from cmk.ccc.user import UserId
from cmk.gui.dashboard.page_view_widget import ViewWidgetEditPage
from tests.testlib.unit.gui.web_test_app import WebTestAppForCMK


def _assert_posts_message_without_inline_script(page: str, message_type: str) -> None:
    assert 'data-cmk_call_ts_function="post_message_to_parent"' in page
    assert message_type in page
    # The bundle that dispatches the call above
    assert "js/main_min.js" in page
    # Inline scripts are blocked by the content security policy
    assert all("src=" in tag for tag in re.findall(r"<script\b[^>]*>", page))


@pytest.mark.usefixtures("patch_theme")
def test_widget_edit_view_posts_configuration_error_to_parent(
    logged_in_admin_wsgi_app: WebTestAppForCMK,
) -> None:
    response = logged_in_admin_wsgi_app.get(
        "/NO_SITE/check_mk/widget_edit_view.py", status=HTTPStatus.OK
    )

    _assert_posts_message_without_inline_script(response.text, "cmk:view:configuration-error")


@pytest.mark.usefixtures("patch_theme")
def test_widget_edit_view_posts_save_completed_to_parent(
    logged_in_admin_wsgi_app: WebTestAppForCMK,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def load_dashboard(owner: UserId, dashboard_name: str) -> dict[str, object]:
        return {"owner": owner, "name": dashboard_name, "embedded_views": {}}

    monkeypatch.setattr(ViewWidgetEditPage, "_load_dashboard", staticmethod(load_dashboard))
    monkeypatch.setattr(ViewWidgetEditPage, "_save", staticmethod(lambda *_args: None))

    response = logged_in_admin_wsgi_app.get(
        "/NO_SITE/check_mk/widget_edit_view.py"
        "?dashboard=main&embedded_id=abc&mode=create&datasource=hosts&_save=1",
        status=HTTPStatus.OK,
    )

    _assert_posts_message_without_inline_script(response.text, "cmk:view:save-completed")
