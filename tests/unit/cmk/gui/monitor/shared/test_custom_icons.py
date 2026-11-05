#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# ruff: noqa: ARG001  # Unused fixtures are needed for setup side effects

from collections.abc import Iterator, Sequence

import pytest

from cmk.ccc.user import UserId
from cmk.gui import sites
from cmk.gui.config import active_config
from cmk.gui.monitor.shared import any_custom_icons, custom_icons, CustomIcon, IconSource
from cmk.gui.openapi.framework.model import ApiOmitted
from cmk.gui.type_defs import IconSpec
from cmk.livestatus_client.testing import MockLiveStatusConnection
from cmk.web.utils.icons import DynamicIconName

pytestmark = pytest.mark.usefixtures("icon_files")


@pytest.fixture(name="user_icons")
def fixture_user_icons(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    with monkeypatch.context() as m:
        m.setattr(
            active_config,
            "user_icons_and_actions",
            {
                "plain": IconSpec({"icon": DynamicIconName("plain"), "title": "Plain"}),
                "in_row": IconSpec(
                    {
                        "icon": DynamicIconName("wiki"),
                        "title": "Wiki",
                        "url": ("https://wiki/$HOSTNAME$/$SERVICEDESC$", "_blank"),
                        "toplevel": True,
                        "sort_index": 10,
                    }
                ),
                "in_menu": IconSpec(
                    {
                        "icon": DynamicIconName("menu"),
                        "title": "Menu",
                        "url": ("https://menu/$HOSTADDRESS$", "_self"),
                    }
                ),
            },
        )
        yield


def _icons(
    actions: str, icon_image: str = "", service_name: str | None = "CPU load"
) -> Sequence[CustomIcon]:
    return custom_icons(
        "host" if service_name is None else "service",
        site_id="local",
        host_name="web-01",
        service_name=service_name,
        source=IconSource(actions=actions, icon_image=icon_image, host_address="10.0.0.1"),
    )


def test_unassigned_icons_are_skipped(with_admin_login: UserId, user_icons: None) -> None:
    assert _icons("") == []


def test_icon_without_action_has_no_url(with_admin_login: UserId, user_icons: None) -> None:
    [icon] = _icons("plain")

    assert (icon.ident, icon.title, icon.url, icon.target) == (
        "plain",
        "Plain",
        ApiOmitted(),
        ApiOmitted(),
    )


def test_action_shown_in_the_row_links_with_macros_replaced(
    with_admin_login: UserId, user_icons: None
) -> None:
    [icon] = _icons("in_row")

    assert (icon.ident, icon.icon_name, icon.icon_path, icon.url, icon.target) == (
        "in_row",
        "wiki",
        ApiOmitted(),
        "https://wiki/web-01/CPU load",
        "_blank",
    )


def test_action_not_shown_in_the_row_is_left_to_the_action_menu(
    with_admin_login: UserId, user_icons: None
) -> None:
    assert _icons("in_menu") == []


def test_icons_are_ordered_by_sort_index(with_admin_login: UserId, user_icons: None) -> None:
    assert [icon.ident for icon in _icons("plain,in_row")] == ["in_row", "plain"]


def test_icon_image_is_an_icon_without_action(with_admin_login: UserId, user_icons: None) -> None:
    [icon] = _icons("", icon_image="logo.png", service_name=None)

    assert (icon.ident, icon.icon_name, icon.icon_path, icon.url) == (
        "icon_image",
        "logo",
        "images/icons/logo.png",
        ApiOmitted(),
    )


@pytest.mark.parametrize(
    "host_name, expected",
    [
        pytest.param(None, True, id="any host"),
        pytest.param("with-icon", True, id="the host with the icon"),
        pytest.param("plain", False, id="another host"),
    ],
)
def test_service_icons_of_one_host_ignore_the_other_hosts(
    request_context: None,
    mock_livestatus: MockLiveStatusConnection,
    host_name: str | None,
    expected: bool,
) -> None:
    mock_livestatus.add_table(
        "services",
        [
            {
                "host_name": name,
                "description": "CPU load",
                "custom_variable_names": [],
                "icon_image": icon_image,
            }
            for name, icon_image in [("with-icon", "logo.png"), ("plain", "")]
        ],
    )
    mock_livestatus.expect_query(["GET services"], match_type="loose")

    with mock_livestatus(expect_status_query=True):
        assert any_custom_icons(sites.live(), "service", host_name=host_name) is expected
