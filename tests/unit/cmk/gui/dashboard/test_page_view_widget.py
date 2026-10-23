#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from http import HTTPStatus

import pytest

from cmk.ccc.user import UserId
from cmk.gui.config import Config
from cmk.gui.dashboard.page_view_widget import ViewWidgetEditPage, ViewWidgetIFrameTokenPage
from cmk.gui.dashboard.store import DashboardStore, get_all_dashboards, save_all_dashboards
from cmk.gui.http import request
from cmk.gui.pages import PageContext
from cmk.gui.permissions import all_permissions
from cmk.gui.type_defs import (
    ColumnSpec,
    ContextFilterConfig,
    ContextualLinkEntryConfig,
    DashboardEmbeddedViewSpec,
)
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.utils.session import session
from cmk.gui.utils.transaction_manager import transactions
from tests.testlib.unit.gui.web_test_app import SetConfig, WebTestAppForCMK
from tests.testlib.unit.rest_api_client import ClientRegistry
from tests.unit.cmk.gui.helpers.dashboard_api_test_helper import create_dashboard_payload
from tests.unit.cmk.gui.helpers.dashboard_widget_resolution_test_helper import dashboard_token
from tests.unit.cmk.gui.helpers.setup_mode_test_helper import form_values


def _assert_posts_message_without_inline_script(page: str, message_type: str) -> None:
    _assert_calls_ts_function_without_inline_script(page, "post_message_to_parent")
    assert message_type in page


def _assert_calls_ts_function_without_inline_script(page: str, function_name: str) -> None:
    assert f'data-cmk_call_ts_function="{function_name}"' in page
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


@pytest.mark.usefixtures("patch_theme")
@pytest.mark.parametrize(
    "wato_enabled, kept_filters",
    [
        pytest.param(True, ["host_labels", "wato_folder"], id="with Setup"),
        pytest.param(False, ["host_labels"], id="folder without Setup"),
    ],
)
def test_widget_edit_view_duplicate_keeps_the_offered_filters_of_a_custom_column_link(
    clients: ClientRegistry,
    with_automation_user: tuple[UserId, str],
    logged_in_admin_wsgi_app: WebTestAppForCMK,
    set_config: SetConfig,
    wato_enabled: bool,
    kept_filters: list[str],
) -> None:
    owner = with_automation_user[0]
    clients.DashboardClient.create_relative_grid_dashboard(create_dashboard_payload("board", {}))
    link = ContextualLinkEntryConfig(
        title="allhosts",
        location=("views", "allhosts"),
        filters=[
            ContextFilterConfig(filter_id="host_labels", key="cmk/os_family"),
            ContextFilterConfig(filter_id="wato_folder"),
        ],
        include_context=False,
        include_time_range=True,
        show_filter_form=False,
    )
    get_all_dashboards()[(owner, "board")]["embedded_views"] = {
        "source": DashboardEmbeddedViewSpec(
            single_infos=[],
            datasource="hosts",
            layout="table",
            painters=[ColumnSpec(name="host", parameters={"color_choices": []})],
            group_painters=[],
            sorters=[],
            browser_reload=0,
            num_columns=1,
            column_headers="pergroup",
            column_links={0: link},
        )
    }
    save_all_dashboards(owner)
    DashboardStore.get_instance.cache_clear()  # type: ignore[attr-defined]

    with set_config(wato_enabled=wato_enabled):
        editor = logged_in_admin_wsgi_app.get(
            "/NO_SITE/check_mk/widget_edit_view.py"
            f"?dashboard=board&owner={owner}&embedded_id=copy&mode=duplicate"
            "&source_embedded_id=source",
            status=HTTPStatus.OK,
        )
        fields = form_values(editor.text, "widget_view")
        # The page's script numbers the entries of each list.
        for name in fields:
            if index := re.search(r"_indexof_(\d+)$", name):
                fields[name] = fields[name] or index.group(1)
        saved = logged_in_admin_wsgi_app.post(
            "/NO_SITE/check_mk/widget_edit_view.py",
            data={**fields, "_save": "1"},
            status=HTTPStatus.OK,
        )
    assert "cmk:view:save-completed" in saved.text, re.findall(
        r"class=\"error\"[^>]*>(.*?)</div>", saved.text
    )
    DashboardStore.get_instance.cache_clear()  # type: ignore[attr-defined]

    copy = get_all_dashboards()[(owner, "board")]["embedded_views"]["copy"]
    kept = [f for f in link["filters"] if f["filter_id"] in kept_filters]
    assert copy.get("column_links") == {0: {**link, "filters": kept}}


@pytest.mark.usefixtures("request_context", "patch_theme")
def test_widget_iframe_token_redirects_to_shared_dashboard() -> None:
    ctx = PageContext(
        config=Config(),
        request=request,
        transactions=transactions,
        session=session,
        user_permissions=UserPermissions.from_config(Config(), all_permissions()),
    )
    request.set_var("widget_id", "any")

    # The token's dashboard does not exist, which disables the token
    with output_funnel.plugged():
        ViewWidgetIFrameTokenPage().get(dashboard_token(), ctx)
        page = "".join(output_funnel.drain())

    _assert_calls_ts_function_without_inline_script(page, "redirect_shared_dashboard")
    assert "shared_dashboard.py?cmk-token=" in page
    # No error message follows the redirect
    assert page.rstrip().endswith("</html>")
