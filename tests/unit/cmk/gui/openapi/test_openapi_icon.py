#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pytest_mock import MockerFixture

from cmk.gui.watolib.icons import IconData
from tests.testlib.unit.rest_api_client import ClientRegistry


def _mock_built_in_icons(mocker: MockerFixture, icons: list[IconData]) -> None:
    mocker.patch(
        "cmk.gui.watolib.icons._available_built_in_icon_data",
        return_value=icons,
    )


def _mock_user_icons(mocker: MockerFixture, icons: list[IconData]) -> None:
    mocker.patch(
        "cmk.gui.watolib.icons._available_user_icon_data",
        return_value=icons,
    )


def _mock_icon_emblems(mocker: MockerFixture, emblems: list[IconData]) -> None:
    mocker.patch(
        "cmk.gui.watolib.icons._available_built_in_icon_emblem_data",
        return_value=emblems,
    )


def test_list_icons(clients: ClientRegistry, mocker: MockerFixture) -> None:
    _mock_built_in_icons(
        mocker,
        [
            IconData(id="icon1", path="", category_id="category1", is_built_in=True),
            IconData(id="icon2", path="", category_id="category2", is_built_in=True),
        ],
    )
    _mock_user_icons(
        mocker,
        [
            IconData(id="icon3", path="", category_id="category3", is_built_in=False),
        ],
    )

    resp = clients.IconClient.get_all()
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code} {resp.body!r}"
    assert len(resp.json["value"]) == 3, "Expected exactly three icons to be returned"

    icons_by_id = {icon["id"]: icon for icon in resp.json["value"]}
    assert icons_by_id["icon1"]["extensions"]["is_built_in"] is True
    assert icons_by_id["icon1"]["extensions"]["category"] == "category1"
    assert icons_by_id["icon2"]["extensions"]["is_built_in"] is True
    assert icons_by_id["icon2"]["extensions"]["category"] == "category2"
    assert icons_by_id["icon3"]["extensions"]["is_built_in"] is False
    assert icons_by_id["icon3"]["extensions"]["category"] == "category3"


def test_list_icons_user_overwrites_built_in(
    clients: ClientRegistry, mocker: MockerFixture
) -> None:
    icon_name = "foo"
    _mock_built_in_icons(
        mocker,
        [
            IconData(id=icon_name, path="", category_id="category1", is_built_in=True),
        ],
    )
    _mock_user_icons(
        mocker,
        [
            IconData(id=icon_name, path="", category_id="category2", is_built_in=False),
        ],
    )

    resp = clients.IconClient.get_all()
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code} {resp.body!r}"
    assert len(resp.json["value"]) == 1, "Expected exactly one icon to be returned"
    icon = resp.json["value"][0]
    assert icon["id"] == icon_name
    assert icon["extensions"]["is_built_in"] is False
    assert icon["extensions"]["category"] == "category2"


def test_list_icon_emblems(clients: ClientRegistry, mocker: MockerFixture) -> None:
    _mock_icon_emblems(
        mocker,
        [
            IconData(id="emblem1", path="", category_id="category1", is_built_in=True),
            IconData(id="emblem2", path="", category_id="category2", is_built_in=True),
        ],
    )

    resp = clients.IconClient.get_all_emblems()
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code} {resp.body!r}"
    assert len(resp.json["value"]) == 2, "Expected exactly two icon emblems to be returned"

    emblems_by_id = {emblem["id"]: emblem for emblem in resp.json["value"]}
    assert emblems_by_id["emblem1"]["extensions"]["category"] == "category1"
    assert emblems_by_id["emblem2"]["extensions"]["category"] == "category2"


def test_list_icon_categories(clients: ClientRegistry) -> None:
    resp = clients.IconClient.get_all_categories()
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code} {resp.body!r}"
    # should be at least the default builtin and user categories
    assert len(resp.json["value"]) >= 2, "Expected at least two icon categories to be returned"
