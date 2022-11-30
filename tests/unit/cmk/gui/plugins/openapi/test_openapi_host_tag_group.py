# !/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

import pytest

from tests.unit.cmk.gui.conftest import WebTestAppForCMK

from cmk.utils.tags import BuiltinTagConfig


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_host_tag_group_update(aut_user_auth_wsgi_app: WebTestAppForCMK):
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
def test_openapi_host_tag_group_get_collection(aut_user_auth_wsgi_app: WebTestAppForCMK):
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
def test_openapi_host_tag_group_delete(aut_user_auth_wsgi_app: WebTestAppForCMK):
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
def test_openapi_host_tag_group_invalid_id(aut_user_auth_wsgi_app: WebTestAppForCMK):
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
def test_openapi_host_tag_group_built_in(aut_user_auth_wsgi_app: WebTestAppForCMK):
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
def test_openapi_host_tag_group_update_use_case(aut_user_auth_wsgi_app: WebTestAppForCMK):
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


def test_openapi_host_tag_with_only_one_option(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    with_host: None,
) -> None:
    base = "/NO_SITE/check_mk/api/1.0"
    wsgi_app = aut_user_auth_wsgi_app
    wsgi_app.call_method(
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

    host = wsgi_app.get(
        base + "/objects/host_config/example.com",
        headers={"Accept": "application/json"},
        status=200,
    )

    wsgi_app.put(
        base + "/objects/host_config/example.com",
        headers={"Accept": "application/json", "If-Match": host.headers["ETag"]},
        content_type="application/json",
        status=200,
        params=json.dumps(
            {
                "attributes": {
                    "alias": "foobar",
                    "tag_group_id999": "pod",
                }
            }
        ),
    )

    host = wsgi_app.get(
        base + "/objects/host_config/example.com",
        headers={"Accept": "application/json"},
        status=200,
    )

    assert host.json["extensions"]["attributes"]["alias"] == "foobar"
    assert host.json["extensions"]["attributes"]["tag_group_id999"] == "pod"

    # TODO: CMK-10899
    # error = wsgi_app.put(
    #     base + "/objects/host_config/example.com",
    #     headers={"Accept": "application/json", "If-Match": host.headers["ETag"]},
    #     content_type="application/json",
    #     status=200,
    #     params=json.dumps(
    #         {
    #             "attributes": {
    #                 "tag_group_id999": "poddy",  # non-existing choice
    #             }
    #         }
    #     ),
    # )
    #
    # assert error.json["detail"].startswith("These fields have problems")
    # assert error.json["fields"] == {"attributes": {"tag_group_id999": ["Unknown field."]}}

    wsgi_app.put(
        base + "/objects/host_config/example.com",
        headers={"Accept": "application/json", "If-Match": host.headers["ETag"]},
        content_type="application/json",
        status=200,
        params=json.dumps(
            {
                "attributes": {
                    "tag_group_id999": None,  # deactivate
                }
            }
        ),
    )

    host = wsgi_app.get(
        base + "/objects/host_config/example.com",
        headers={"Accept": "application/json"},
        status=200,
    )

    assert host.json["extensions"]["attributes"]["tag_group_id999"] is None


def test_openapi_host_tag_groups_all_props_in_schema(
    aut_user_auth_wsgi_app: WebTestAppForCMK, base: str
) -> None:
    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/domain-types/host_tag_group/collections/all",
        headers={"Accept": "application/json"},
        status=200,
    )
    first_tag = resp.json["value"][0]
    assert "title" in first_tag
    assert "id" in first_tag
    assert "topic" in first_tag["extensions"]
    assert "tags" in first_tag["extensions"]


def test_openapi_host_tags_groups_without_topic_and_tags(
    aut_user_auth_wsgi_app: WebTestAppForCMK, base: str
) -> None:
    aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/domain-types/host_tag_group/collections/all",
        params=json.dumps(
            {
                "ident": "group_id999",
                "title": "Kubernetes",
                "help": "Kubernetes Pods",
                "tags": [{"ident": "pod", "title": "Pod"}],
            }
        ),
        headers={"Accept": "application/json"},
        status=200,
        content_type="application/json",
    )

    individual_resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/objects/host_tag_group/group_id999",
        headers={"Accept": "application/json"},
        status=200,
    )

    assert individual_resp.json["extensions"]["topic"] == "Tags"

    # Let's see if outward validation works here as well
    aut_user_auth_wsgi_app.get(
        base + "/domain-types/host_tag_group/collections/all",
        headers={"Accept": "application/json"},
        status=200,
    )
