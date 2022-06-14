# !/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

import pytest

from cmk.utils.tags import BuiltinTagConfig

from tests.unit.cmk.gui.conftest import WebTestAppForCMK


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_host_tag_group_update(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    base = "/NO_SITE/check_mk/api/1.0"

    resp = aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/domain-types/host_tag_group/collections/all",
        params=json.dumps(
            {
                "ident": "foo",
                "title": "foobar",
                "topic": "nothing",
                "tags": [
                    {
                        "ident": "tester",
                        "title": "something",
                    }
                ],
            }
        ),
        headers={"Accept": "application/json"},
        status=200,
        content_type="application/json",
    )

    _resp = aut_user_auth_wsgi_app.call_method(
        "put",
        base + "/objects/host_tag_group/foo",
        params=json.dumps(
            {
                "tags": [
                    {
                        "ident": "tutu",
                        "title": "something",
                    }
                ]
            }
        ),
        headers={"If-Match": resp.headers["ETag"], "Accept": "application/json"},
        status=200,
        content_type="application/json",
    )

    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/objects/host_tag_group/foo",
        headers={"Accept": "application/json"},
        status=200,
    )
    assert resp.json["extensions"] == {
        "tags": [{"id": "tutu", "title": "something", "aux_tags": []}],
        "topic": "nothing",
    }


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_host_tag_group_get_collection(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    base = "/NO_SITE/check_mk/api/1.0"

    builtin_groups_count = len(BuiltinTagConfig().tag_groups)

    col_resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/domain-types/host_tag_group/collections/all",
        headers={"Accept": "application/json"},
        status=200,
    )
    assert len(col_resp.json_body["value"]) == builtin_groups_count


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_host_tag_group_delete(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    base = "/NO_SITE/check_mk/api/1.0"

    resp = aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/domain-types/host_tag_group/collections/all",
        params=json.dumps(
            {
                "ident": "foo",
                "title": "foobar",
                "topic": "nothing",
                "tags": [
                    {
                        "ident": "tester",
                        "title": "something",
                    }
                ],
            }
        ),
        headers={"Accept": "application/json"},
        status=200,
        content_type="application/json",
    )

    _resp = aut_user_auth_wsgi_app.call_method(
        "delete",
        base + "/objects/host_tag_group/foo",
        params=json.dumps({}),
        headers={"If-Match": resp.headers["ETag"], "Accept": "application/json"},
        status=204,
        content_type="application/json",
    )

    _resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/objects/host_tag_group/foo",
        headers={"Accept": "application/json"},
        status=404,
    )


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_host_tag_group_invalid_id(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    base = "/NO_SITE/check_mk/api/1.0"
    _resp = aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/domain-types/host_tag_group/collections/all",
        params=json.dumps(
            {
                "ident": "1",
                "title": "Kubernetes",
                "topic": "Data Sources",
                "help": "Kubernetes Pods",
                "tags": [{"ident": "pod", "title": "Pod"}],
            }
        ),
        headers={"Accept": "application/json"},
        status=400,
        content_type="application/json",
    )


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_host_tag_group_built_in(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    base = "/NO_SITE/check_mk/api/1.0"

    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/domain-types/host_tag_group/collections/all",
        headers={"Accept": "application/json"},
        status=200,
    )
    built_in_tags = [tag_group.title for tag_group in BuiltinTagConfig().tag_groups]
    assert all(
        title in (entry["title"] for entry in resp.json_body["value"]) for title in built_in_tags
    )

    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/objects/host_tag_group/agent",
        headers={"Accept": "application/json"},
        status=200,
    )

    _resp = aut_user_auth_wsgi_app.call_method(
        "put",
        base + "/objects/host_tag_group/agent",
        params=json.dumps(
            {
                "tags": [
                    {
                        "ident": "tutu",
                        "title": "something",
                    }
                ]
            }
        ),
        headers={"If-Match": resp.headers["ETag"], "Accept": "application/json"},
        status=405,
        content_type="application/json",
    )

    _resp = aut_user_auth_wsgi_app.call_method(
        "delete",
        base + "/objects/host_tag_group/agent",
        params=json.dumps({}),
        headers={"Accept": "application/json"},
        status=405,
        content_type="application/json",
    )


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_host_tag_group_update_use_case(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    base = "/NO_SITE/check_mk/api/1.0"
    resp = aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/domain-types/host_tag_group/collections/all",
        params=json.dumps(
            {
                "ident": "group_id999",
                "title": "Kubernetes",
                "topic": "Data Sources",
                "help": "Kubernetes Pods",
                "tags": [{"ident": "pod", "title": "Pod"}],
            }
        ),
        headers={"Accept": "application/json"},
        status=200,
        content_type="application/json",
    )

    _resp = aut_user_auth_wsgi_app.call_method(
        "put",
        base + "/objects/host_tag_group/group_id999",
        params=json.dumps(
            {
                "title": "Kubernetes",
                "topic": "Data Sources",
                "help": "Kubernetes Pods",
                "tags": [{"ident": "pod", "title": "Pod"}],
            }
        ),
        headers={"If-Match": resp.headers["ETag"], "Accept": "application/json"},
        status=200,
        content_type="application/json",
    )

    _ = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/objects/host_tag_group/group_id999",
        headers={"Accept": "application/json"},
        status=200,
    )
