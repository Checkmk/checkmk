#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
smth (needed for endpoint registration in test_openapi_endpoint_decorator_resets_used_permissions)
"""

import json
from typing import Any, Mapping

import pytest

from tests.unit.cmk.gui.conftest import WebTestAppForCMK

from cmk.gui.fields.utils import BaseSchema
from cmk.gui.globals import request_local_attr
from cmk.gui.http import Response
from cmk.gui.plugins.openapi.restful_objects.decorators import Endpoint, WrappedEndpoint
from cmk.gui.plugins.openapi.restful_objects.endpoint_registry import ENDPOINT_REGISTRY
from cmk.gui.plugins.openapi.utils import ProblemException
from cmk.gui.utils.script_helpers import session_wsgi_app

from cmk import fields

endpoint = request_local_attr("endpoint")


def test_openapi_accept_header_missing(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        "/NO_SITE/check_mk/api/1.0/domain-types/folder_config/collections/all",
        status=406,
    )
    assert resp.json == {
        "detail": "Please specify an Accept Header.",
        "status": 406,
        "title": "Not Acceptable",
    }


def test_openapi_accept_header_matches(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        "/NO_SITE/check_mk/api/1.0/domain-types/folder_config/collections/all",
        {},  # params
        {"Accept": "application/json"},  # headers
        status=200,
    )
    assert resp.json["value"] == []


def test_openapi_accept_header_invalid(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        "/NO_SITE/check_mk/api/1.0/domain-types/folder_config/collections/all",
        {},  # params
        {"Accept": "asd-asd-asd"},  # headers
        status=406,
    )
    assert resp.json == {
        "detail": "Can not send a response with the content type specified in the "
        "'Accept' Header. Accept Header: asd-asd-asd. Supported content "
        "types: [application/json]",
        "status": 406,
        "title": "Not Acceptable",
    }


class SomeSchema(BaseSchema):
    permission = fields.String(description="smth", example="smth")


@pytest.fixture(name="test_endpoint")
def install_endpoint():
    session_wsgi_app.cache_clear()

    @Endpoint(
        path="/unitest-endpoint-test-that-is-not-cleaned-up",
        method="post",
        link_relation="help",
        output_empty=True,
        tag_group="Monitoring",
        request_schema=SomeSchema,
        update_config_generation=False,
        skip_locking=True,
    )
    def test(param: Mapping[str, Any]) -> Response:
        """Smth"""
        endpoint.remember_checked_permission(param["body"]["permission"])
        return Response(status=204)

    yield test

    ENDPOINT_REGISTRY.remove_endpoint(test.endpoint)


def test_openapi_endpoint_decorator_resets_used_permissions(
    test_endpoint: WrappedEndpoint, aut_user_auth_wsgi_app: WebTestAppForCMK
) -> None:
    """
    before this test, the Endpoint._used_permissions set was not cleared
    between request. so if the endpoint had different code paths with different
    requested permissions, no error was reported (depending on the order the
    different code paths were called), although it should have.
    for example: delete a downtime. if the downtime exists, the permission
    'action.downtime' was requested, if the downtime did not exist it was not
    requested.
    once an existing downtime was deleted, all other calls with non existing
    downtimes would have passed, but should have raised an error, that the
    permission "action.downtime" was not requested.
    """

    def call(permission: str) -> None:
        aut_user_auth_wsgi_app.call_method(
            "post",
            "/NO_SITE/check_mk/api/1.0/unitest-endpoint-test-that-is-not-cleaned-up",
            json.dumps({"permission": permission}),  # params
            {"Accept": "application/json"},  # headers
            content_type="application/json",
            status=204,
        )

    # here we create a code path, that requests the permission "one"
    call("one")
    # we expect to see this permission in the collection:
    assert test_endpoint.endpoint._used_permissions == set(["one"])
    # then we create a code path that requests the permission "two"
    call("two")
    # and expect only "two" in the collection, because "one" was requested in
    # another call. before the fix, both "one" and "two" were in this set.
    assert test_endpoint.endpoint._used_permissions == set(["two"])


@pytest.fixture(name="test_endpoint_raise_status_code")
def install_endpoint_raise():
    session_wsgi_app.cache_clear()

    @Endpoint(
        path="/raise_exception",
        method="get",
        link_relation="help",
        output_empty=True,
        tag_group="Monitoring",
        update_config_generation=False,
        skip_locking=True,
    )
    def test(param: Mapping[str, Any]) -> Response:
        """Smth"""
        raise ProblemException(418, "short", "long")

    yield test

    ENDPOINT_REGISTRY.remove_endpoint(test.endpoint)


def test_openapi_endpoint_decorator_catches_status_code_exceptions(
    test_endpoint_raise_status_code: WrappedEndpoint, aut_user_auth_wsgi_app: WebTestAppForCMK
) -> None:
    """
    before this test, the Endpoint did not check for exceptions that change the
    status code, but only for responses that return the wrong status code.
    """

    response = aut_user_auth_wsgi_app.call_method(
        "get",
        "/NO_SITE/check_mk/api/1.0/raise_exception",
        "",
        {"Accept": "application/json"},  # headers
        status=500,
    )
    assert json.loads(response.text) == {
        "title": "Unexpected status code returned: 418",
        "status": 500,
        "detail": "Endpoint tests.unit.cmk.gui.plugins.openapi.test_endpoint.test\nThis is a bug, please report.",
        "ext": {"codes": [204]},
    }
