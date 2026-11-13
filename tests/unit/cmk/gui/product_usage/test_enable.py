#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.site import omd_site
from cmk.gui.config import Config
from cmk.gui.exceptions import MKAuthException
from cmk.gui.http import request
from cmk.gui.pages import PageContext
from cmk.gui.product_usage_analytics.enable import AjaxEnableProductUsageAnalytics
from cmk.gui.session import session
from cmk.gui.watolib.activate_changes import get_pending_changes
from cmk.gui.watolib.global_settings import load_configuration_settings, save_global_settings


def _page_context() -> PageContext:
    request.set_var("_csrf_token", str(session.session_info.csrf_token))
    return PageContext(config=Config(), request=request)


@pytest.mark.usefixtures("request_context", "with_admin_login")
def test_enabling_keeps_the_proxy_setting() -> None:
    save_global_settings(
        {
            "product_usage_analytics": {
                "enabled": "not_decided",
                "proxy_setting": ("global", "corporate_proxy"),
            }
        }
    )

    AjaxEnableProductUsageAnalytics().page(_page_context())

    assert load_configuration_settings()["product_usage_analytics"] == {
        "enabled": "enabled",
        "proxy_setting": ("global", "corporate_proxy"),
    }


@pytest.mark.usefixtures("request_context", "with_admin_login")
def test_enabling_is_a_pending_change() -> None:
    AjaxEnableProductUsageAnalytics().page(_page_context())

    assert [change.action_name for change in get_pending_changes([omd_site()]).values()] == [
        "edit-configvar"
    ]


@pytest.mark.usefixtures("request_context", "with_user_login")
def test_users_without_permission_for_global_settings_cannot_enable() -> None:
    with pytest.raises(MKAuthException):
        AjaxEnableProductUsageAnalytics().page(_page_context())

    assert "product_usage_analytics" not in load_configuration_settings()
