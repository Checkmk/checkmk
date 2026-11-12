#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import html
import json
import re
import time
from collections.abc import Mapping

import pytest
from werkzeug.test import create_environ

from cmk.ccc.user import UserId
from cmk.gui.config import Config
from cmk.gui.http import Request, Response
from cmk.gui.logged_in import LoggedInUser, UserDefaultConfig
from cmk.gui.product_usage_analytics.popup import (
    ENABLED_CHOICE_ID,
    render_product_usage_analytics_popup,
)
from cmk.gui.role_types import BuiltInUserRole, CustomUserRole
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.roles import UserPermissions

_COOKIE_NAME = "product_usage_analytics_popup_timestamp"
_DAY = 24 * 60 * 60


def _request_with_reminder_from(seconds_ago: float) -> Request:
    return Request(
        create_environ(headers={"Cookie": f"{_COOKIE_NAME}={time.time() - seconds_ago}"})
    )


def _admin(config: Config, permissions: Mapping[str, bool] | None = None) -> LoggedInUser:
    admin_id = UserId("admin")
    roles: dict[str, BuiltInUserRole | CustomUserRole] = {
        **config.roles,
        "admin": BuiltInUserRole(
            alias="Administrator",
            permissions=dict(permissions or {"wato.global": True}),
            builtin=True,
        ),
    }
    return LoggedInUser(
        admin_id,
        UserPermissions(roles, {}, {admin_id: ["admin"]}, []),
        defaults=UserDefaultConfig(
            users={}, default_language="en", default_show_mode="default_show_less"
        ),
    )


def _popup_data(rendered: str) -> dict[str, object]:
    match = re.search(r'<cmk-product-usage-analytics data="([^"]*)"', rendered)
    assert match
    data = json.loads(html.unescape(match.group(1)))
    assert isinstance(data, dict)
    return data


def _render_due_popup(config: Config, user: LoggedInUser) -> str:
    with output_funnel.plugged():
        render_product_usage_analytics_popup(
            config, user, _request_with_reminder_from(31 * _DAY), Response()
        )
        return output_funnel.drain()


def _set_cookies(response: Response) -> list[str]:
    return response.headers.getlist("Set-Cookie")


@pytest.mark.usefixtures("request_context")
def test_popup_is_shown_once_the_reminder_is_due() -> None:
    config = Config()
    response = Response()

    with output_funnel.plugged():
        render_product_usage_analytics_popup(
            config, _admin(config), _request_with_reminder_from(31 * _DAY), response
        )
        rendered = output_funnel.drain()

    assert "cmk-product-usage-analytics" in rendered


@pytest.mark.usefixtures("request_context")
def test_showing_the_popup_does_not_postpone_the_next_reminder() -> None:
    config = Config()
    response = Response()

    with output_funnel.plugged():
        render_product_usage_analytics_popup(
            config, _admin(config), _request_with_reminder_from(31 * _DAY), response
        )

    assert not any(cookie.startswith(f"{_COOKIE_NAME}=") for cookie in _set_cookies(response))


@pytest.mark.usefixtures("request_context")
def test_popup_is_not_shown_before_the_reminder_is_due() -> None:
    config = Config()
    response = Response()

    with output_funnel.plugged():
        render_product_usage_analytics_popup(
            config, _admin(config), _request_with_reminder_from(29 * _DAY), response
        )
        rendered = output_funnel.drain()

    assert "cmk-product-usage-analytics" not in rendered


@pytest.mark.usefixtures("request_context")
def test_popup_enables_the_setting_with_the_choice_of_the_global_settings_form() -> None:
    config = Config()

    data = _popup_data(_render_due_popup(config, _admin(config)))

    assert data["enabled_choice_id"] == ENABLED_CHOICE_ID


@pytest.mark.usefixtures("request_context")
def test_popup_is_not_shown_without_permission_for_global_settings() -> None:
    config = Config()

    rendered = _render_due_popup(config, _admin(config, {"wato.global": False}))

    assert "cmk-product-usage-analytics" not in rendered


@pytest.mark.usefixtures("request_context")
def test_popup_is_not_shown_in_read_only_mode() -> None:
    config = Config(wato_read_only={"enabled": True, "message": "", "rw_users": []})

    rendered = _render_due_popup(config, _admin(config))

    assert "cmk-product-usage-analytics" not in rendered
