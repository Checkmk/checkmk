#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import random
import string

import pytest

from tests.unit.cmk.gui.conftest import WebTestAppForCMK

from cmk.utils import version

managedtest = pytest.mark.skipif(not version.is_managed_edition(), reason="see #7213")


@managedtest
@pytest.mark.parametrize("group_type", ["host", "contact", "service"])
def test_openapi_groups(group_type, aut_user_auth_wsgi_app: WebTestAppForCMK):

    name = _random_string(10)
    alias = _random_string(10)

    group = {"name": name, "alias": alias, "customer": "provider"}

    base = "/NO_SITE/check_mk/api/1.0"
    resp = aut_user_auth_wsgi_app.call_method(
        "post",
        base + f"/domain-types/{group_type}_group_config/collections/all",
        params=json.dumps(group),
        status=200,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )

    _ = aut_user_auth_wsgi_app.call_method(
        "get",
        base + f"/domain-types/{group_type}_group_config/collections/all",
        status=200,
        headers={"Accept": "application/json"},
    )

    resp = aut_user_auth_wsgi_app.follow_link(
        resp,
        "self",
        status=200,
        headers={"Accept": "application/json"},
    )

    update_group = {"alias": f"{alias} update"}

    aut_user_auth_wsgi_app.follow_link(
        resp,
        ".../update",
        params=json.dumps(update_group),
        headers={"If-Match": "foo bar", "Accept": "application/json"},
        status=412,
        content_type="application/json",
    )

    resp = aut_user_auth_wsgi_app.follow_link(
        resp,
        ".../update",
        params=json.dumps(update_group),
        headers={"If-Match": resp.headers["ETag"], "Accept": "application/json"},
        status=200,
        content_type="application/json",
    )

    aut_user_auth_wsgi_app.follow_link(
        resp,
        ".../delete",
        status=204,
        headers={"Accept": "application/json"},
        content_type="application/json",
    )


@managedtest
@pytest.mark.parametrize("group_type", ["host", "service", "contact"])
def test_openapi_bulk_groups(
    group_type,
    aut_user_auth_wsgi_app: WebTestAppForCMK,
):

    groups = [
        {"name": _random_string(10), "alias": _random_string(10), "customer": "provider"}
        for _i in range(2)
    ]

    base = "/NO_SITE/check_mk/api/1.0"
    resp = aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/domain-types/%s_group_config/actions/bulk-create/invoke" % (group_type,),
        params=json.dumps({"entries": groups}),
        headers={"Accept": "application/json"},
        status=200,
        content_type="application/json",
    )
    assert len(resp.json["value"]) == 2

    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + f"/objects/{group_type}_group_config/{groups[0]['name']}",
        status=200,
        headers={"Accept": "application/json"},
    )
    assert resp.json_body["extensions"]["customer"] == "provider"

    _resp = aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/domain-types/%s_group_config/actions/bulk-create/invoke" % (group_type,),
        params=json.dumps({"entries": groups}),
        headers={"Accept": "application/json"},
        status=400,
        content_type="application/json",
    )

    update_groups = [
        {
            "name": group["name"],
            "attributes": {"alias": group["alias"], "customer": "global"},
        }
        for group in groups
    ]

    _resp = aut_user_auth_wsgi_app.call_method(
        "put",
        base + "/domain-types/%s_group_config/actions/bulk-update/invoke" % (group_type,),
        params=json.dumps({"entries": update_groups}),
        headers={"Accept": "application/json"},
        status=200,
        content_type="application/json",
    )

    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + f"/objects/{group_type}_group_config/{groups[0]['name']}",
        status=200,
        headers={"Accept": "application/json"},
    )
    assert resp.json_body["extensions"]["customer"] == "global"

    partial_update_groups = [
        {
            "name": group["name"],
            "attributes": {
                "alias": f"{group['alias']} partial",
            },
        }
        for group in groups
    ]

    _resp = aut_user_auth_wsgi_app.call_method(
        "put",
        base + "/domain-types/%s_group_config/actions/bulk-update/invoke" % (group_type,),
        params=json.dumps({"entries": partial_update_groups}),
        headers={"Accept": "application/json"},
        status=200,
        content_type="application/json",
    )

    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + f"/objects/{group_type}_group_config/{groups[0]['name']}",
        headers={"Accept": "application/json"},
        status=200,
    )
    assert resp.json_body["extensions"]["customer"] == "global"

    _resp = aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/domain-types/%s_group_config/actions/bulk-delete/invoke" % (group_type,),
        params=json.dumps({"entries": [f"{group['name']}" for group in groups]}),
        headers={"Accept": "application/json"},
        status=204,
        content_type="application/json",
    )


@managedtest
@pytest.mark.parametrize("group_type", ["host", "contact", "service"])
def test_openapi_groups_with_customer(
    group_type,
    aut_user_auth_wsgi_app: WebTestAppForCMK,
):

    name = _random_string(10)
    alias = _random_string(10)

    group = {"name": name, "alias": alias, "customer": "global"}

    base = "/NO_SITE/check_mk/api/1.0"
    _resp = aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/domain-types/%s_group_config/collections/all" % (group_type,),
        params=json.dumps(group),
        headers={"Accept": "application/json"},
        status=200,
        content_type="application/json",
    )

    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + f"/objects/{group_type}_group_config/{name}",
        headers={"Accept": "application/json"},
        status=200,
    )
    assert resp.json_body["extensions"]["customer"] == "global"

    resp = aut_user_auth_wsgi_app.call_method(
        "put",
        base + f"/objects/{group_type}_group_config/{name}",
        headers={"If-Match": resp.headers["ETag"], "Accept": "application/json"},
        params=json.dumps(
            {
                "alias": f"{alias}+",
            }
        ),
        status=200,
        content_type="application/json",
    )
    assert resp.json_body["extensions"]["customer"] == "global"

    resp = aut_user_auth_wsgi_app.call_method(
        "put",
        base + f"/objects/{group_type}_group_config/{name}",
        headers={"If-Match": resp.headers["ETag"], "Accept": "application/json"},
        params=json.dumps({"alias": alias, "customer": "provider"}),
        status=200,
        content_type="application/json",
    )
    assert resp.json_body["extensions"]["customer"] == "provider"


@managedtest
@pytest.mark.parametrize("group_type", ["host", "contact", "service"])
def test_openapi_group_values_are_links(group_type, wsgi_app, with_automation_user):
    username, secret = with_automation_user
    wsgi_app.set_authorization(("Bearer", username + " " + secret))

    base = "/NO_SITE/check_mk/api/1.0"
    postfix = f"/domain-types/{group_type}_group_config/collections/all"
    url = f"{base}{postfix}"

    group = {"name": "foo_bar", "alias": "foo bar", "customer": "global"}
    _response = wsgi_app.call_method(
        "post",
        base + f"/domain-types/{group_type}_group_config/collections/all",
        params=json.dumps(group),
        headers={"Accept": "application/json"},
        status=200,
        content_type="application/json",
    )

    response = wsgi_app.call_method(url=url, method="GET", headers={"Accept": "application/json"})
    assert response.status_code == 200

    json_data = response.json
    assert len(json_data["value"]) == 1
    assert json_data["value"][0]["domainType"] == "link"


def _random_string(size):
    return "".join(random.choice(string.ascii_letters + string.digits) for _ in range(size))
