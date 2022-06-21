#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

import pytest

from tests.unit.cmk.gui.conftest import WebTestAppForCMK


@pytest.fixture(name="object_base")
def user_role_object_base(base: str) -> str:
    return f"{base}/objects/user_role/"


@pytest.fixture(name="collection_base")
def user_role_collection_base(base: str) -> str:
    return f"{base}/domain-types/user_role/collections/all"


def test_get_userrole_endpoint(object_base: str, aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    resp = aut_user_auth_wsgi_app.get(
        object_base + "admin",
        status=200,
        headers={"Accept": "application/json"},
    )

    assert resp.json["extensions"].keys() == {"alias", "permissions", "builtin"}
    assert {link["method"] for link in resp.json["links"]} == {"GET", "PUT"}


def test_get_userroles_endpoint(
    collection_base: str, aut_user_auth_wsgi_app: WebTestAppForCMK
) -> None:
    resp = aut_user_auth_wsgi_app.get(
        collection_base,
        status=200,
        headers={"Accept": "application/json"},
    )

    assert {user_role["id"] for user_role in resp.json["value"]} == {"user", "admin", "guest"}


def test_post_userrole_endpoint(
    collection_base: str, object_base: str, aut_user_auth_wsgi_app: WebTestAppForCMK
) -> None:
    aut_user_auth_wsgi_app.post(
        collection_base,
        status=200,
        params=json.dumps({"role_id": "admin"}),
        headers={"Accept": "application/json"},
        content_type="application/json",
    )

    resp = aut_user_auth_wsgi_app.get(
        object_base + "adminx",
        status=200,
        headers={"Accept": "application/json"},
    )

    assert resp.json["extensions"].keys() == {"alias", "permissions", "builtin", "basedon"}
    assert resp.json["id"] == "adminx"
    assert {link["method"] for link in resp.json["links"]} == {"GET", "PUT", "DELETE"}


def test_delete_userrole_endpoint(
    collection_base: str, object_base: str, aut_user_auth_wsgi_app: WebTestAppForCMK
) -> None:
    aut_user_auth_wsgi_app.post(
        collection_base,
        status=200,
        params=json.dumps({"role_id": "admin"}),
        headers={"Accept": "application/json"},
        content_type="application/json",
    )

    aut_user_auth_wsgi_app.delete(
        object_base + "adminx",
        status=204,
        headers={"Accept": "application/json"},
    )


def test_delete_non_existing_userrole_endpoint(
    object_base: str, aut_user_auth_wsgi_app: WebTestAppForCMK
) -> None:
    aut_user_auth_wsgi_app.delete(
        object_base + "non-existing-user-role",
        status=404,
        headers={"Accept": "application/json"},
    )


def test_delete_builtin_userrole(
    object_base: str, aut_user_auth_wsgi_app: WebTestAppForCMK
) -> None:
    aut_user_auth_wsgi_app.delete(
        object_base + "admin",
        status=404,
        headers={"Accept": "application/json"},
    )
