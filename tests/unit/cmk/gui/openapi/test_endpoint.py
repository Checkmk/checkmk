#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


"""
smth (needed for endpoint registration in test_openapi_endpoint_decorator_resets_used_permissions)
"""

import base64
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from unittest import mock

import pytest

from tests.testlib.unit.rest_api_client import ClientRegistry, RestApiClient

from tests.unit.cmk.web_test_app import SetConfig, WebTestAppForCMK

from cmk.utils.local_secrets import SiteInternalSecret

from cmk.gui import hooks
from cmk.gui.fields.utils import BaseSchema
from cmk.gui.http import Response
from cmk.gui.openapi.restful_objects.decorators import Endpoint, WrappedEndpoint
from cmk.gui.openapi.restful_objects.registry import endpoint_registry
from cmk.gui.openapi.utils import ProblemException, RestAPIResponseGeneralException

from cmk import fields

TEST_TARGZ_FILE = "H4sIAAAAAAAAA+3OQQrCMBCF4aw9RbyAJDVNzxNooIXgyBjR4xvppuBCN0UK/7eYxzCzeNN8qs9qNuWaGMM7/dC7dS58b3yI3RDbDJ1pe/BnY922tRb3W01qrSlZLklHueaqounj79t9p6ZcitiHaBmPh3+XAQAAAAAAAAAAAAAAAAD87AUCVDjzACgAAA=="


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
def install_endpoint(fresh_app_instance):
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
        hooks.call("permission-checked", param["body"]["permission"])
        return Response(status=204)

    endpoint_registry.register(test, ignore_duplicates=False)

    yield test

    endpoint_registry.unregister(test)


@pytest.fixture(name="test_multiple_accept_endpoint")
def install_multi_accept_endpoint(fresh_app_instance):
    @Endpoint(
        path="/test_multiple_content_types",
        method="post",
        link_relation="help",
        tag_group="Checkmk Internal",
        content_type="application/json",
        update_config_generation=False,
        skip_locking=True,
        accept=["application/json", "application/gzip"],
        request_schema=SomeSchema,
        response_schema=SomeSchema,
    )
    def multiaccept_test(param: Mapping[str, Any]) -> Response:
        response = Response()
        response.set_content_type("application/json")
        response.set_data(json.dumps({"permission": param.get("content_type")}))
        response.status_code = 200
        return response

    endpoint_registry.register(multiaccept_test, ignore_duplicates=False)

    yield multiaccept_test

    endpoint_registry.unregister(multiaccept_test)


@pytest.fixture(name="test_internal_endpoint")
def install_reserved_endpoint(fresh_app_instance):
    @Endpoint(
        path="/i_am_reserved",
        method="get",
        link_relation="help",
        tag_group="Monitoring",
        output_empty=True,
        internal_user_only=True,
    )
    def reserved_test(param: Mapping[str, Any]) -> Response:
        return Response(status=204)

    endpoint_registry.register(reserved_test, ignore_duplicates=False)

    yield reserved_test

    endpoint_registry.unregister(reserved_test)


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
    assert test_endpoint.endpoint._used_permissions == {"one"}
    # then we create a code path that requests the permission "two"
    call("two")
    # and expect only "two" in the collection, because "one" was requested in
    # another call. before the fix, both "one" and "two" were in this set.
    assert test_endpoint.endpoint._used_permissions == {"two"}


@pytest.fixture(name="test_endpoint_raise_status_code")
def install_endpoint_raise(fresh_app_instance):
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

    endpoint_registry.register(test, ignore_duplicates=False)
    yield test

    endpoint_registry.unregister(test)


@pytest.fixture(name="test_endpoint_accept_parameter")
def accept_parameter_endpoint(fresh_app_instance):
    @Endpoint(
        path="/test_accept_parameter",
        method="post",
        link_relation="help",
        output_empty=True,
        tag_group="Checkmk Internal",
        accept="application/gzip",
        update_config_generation=False,
        skip_locking=True,
    )
    def test(param: Mapping[str, Any]) -> Response:
        """Smth"""
        return Response(status=204)

    endpoint_registry.register(test, ignore_duplicates=False)
    yield test

    endpoint_registry.unregister(test)


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
    response.assert_rest_api_crash()
    assert response.json["title"] == "Internal Server Error"
    assert response.json["ext"]["exc_type"] == "RestAPIResponseException"
    exc = response.json["ext"]["details"]["rest_api_exception"]
    assert exc["description"] == "Unexpected status code returned: 418"
    assert exc["detail"] == "Endpoint tests.unit.cmk.gui.openapi.test_endpoint.test"
    assert set(exc["ext"]["The following status codes are allowed for this endpoint"]) == {406, 204}


# ========= PATH Validation Tests =========
def test_path_validation_exception(base: str, aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    resp = aut_user_auth_wsgi_app.get(
        url=f"{base}/objects/event_console/abc",
        headers={"Accept": "application/json"},
        status=404,
    )
    assert resp.json["title"] == "Not Found"
    assert resp.json["detail"] == "These fields have problems: event_id"
    assert resp.json["fields"] == {"event_id": ["'abc' does not match pattern '^[0-9]+$'."]}


# ========= HEADER Validation Tests =========
def test_non_matching_content_type_exception(
    base: str, aut_user_auth_wsgi_app: WebTestAppForCMK
) -> None:
    test_data: dict = {
        "name": "foo",
        "alias": "foobar",
        "active_time_ranges": [{"day": "all"}],
        "exceptions": [{"date": "2020-01-01"}],
    }
    resp = aut_user_auth_wsgi_app.post(
        url=f"{base}/domain-types/time_period/collections/all",
        headers={"Accept": "application/json", "Content-Type": "text"},
        params=json.dumps(test_data),
        status=415,
    )
    assert resp.json["title"] == "Content type not valid for this endpoint."
    assert resp.json["detail"] == "Content-Type 'text' not supported for this endpoint."


def test_content_type_with_invalid_charset(
    base: str, aut_user_auth_wsgi_app: WebTestAppForCMK
) -> None:
    test_data: dict = {
        "name": "foo",
        "alias": "foobar",
        "active_time_ranges": [{"day": "all"}],
        "exceptions": [{"date": "2020-01-01"}],
    }
    resp = aut_user_auth_wsgi_app.post(
        url=f"{base}/domain-types/time_period/collections/all",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json; charset=not-utf-8",
        },
        params=json.dumps(test_data),
        status=415,
    )
    assert resp.json["title"] == "Content type not valid for this endpoint."
    assert (
        resp.json["detail"]
        == "Character set 'not-utf-8' not supported for content-type 'application/json'."
    )


def test_non_supported_accept_header(base: str, aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    test_data: dict = {
        "name": "foo",
        "alias": "foobar",
        "active_time_ranges": [{"day": "all"}],
        "exceptions": [{"date": "2020-01-01"}],
    }
    resp = aut_user_auth_wsgi_app.post(
        url=f"{base}/domain-types/time_period/collections/all",
        headers={"Accept": "something_else", "Content-Type": "application/json"},
        params=json.dumps(test_data),
        status=406,
    )
    assert resp.json["title"] == "Not Acceptable"
    assert (
        resp.json["detail"]
        == "Can not send a response with the content type specified in the 'Accept' Header. Accept Header: something_else. Supported content types: [application/json]"
    )


# ========= WATO disabled Validation =========
def test_wato_disabled_exception(clients: ClientRegistry, set_config: SetConfig) -> None:
    test_data: dict[str, Any] = {
        "aux_tag_id": "aux_tag_id_1",
        "title": "aux_tag_1",
        "topic": "topic_1",
        "help": "HELP",
    }
    with set_config(wato_enabled=False):
        resp = clients.AuxTag.create(
            tag_data=test_data,
            expect_ok=False,
        )
    resp.assert_status_code(403)
    assert resp.json["title"] == "Forbidden: Setup is disabled"
    assert (
        resp.json["detail"]
        == "This endpoint is currently disabled via the 'Disable remote configuration' option in 'Distributed Monitoring'. You may be able to query the central site."
    )


# ========= Permission Validation =========
def test_permission_exception(clients: ClientRegistry) -> None:
    def validate(*args, **kwargs):
        return False

    with mock.patch("cmk.gui.utils.permission_verification.BasePerm.validate", validate):
        resp = clients.AuxTag.get(aux_tag_id="ping", expect_ok=False)

    resp.assert_rest_api_crash()

    assert resp.json["ext"]["exc_type"] == "RestAPIPermissionException"
    exc = resp.json["ext"]["details"]["rest_api_exception"]
    assert exc["description"] == "Permission mismatch"
    assert exc["detail"] == (
        "There can be some causes for this error:\n"
        "* a permission which was required (successfully) was not declared\n"
        "* a permission which was declared (not optional) was not required\n"
        "* No permission was required at all, although permission were declared\n"
        "Endpoint: <Endpoint cmk.gui.openapi.endpoints.aux_tags:show_aux_tag>\n"
        "Params: {'aux_tag_id': 'ping'}\n"
        "Required: ['wato.hosttags']\nDeclared: {wato.hosttags}\n"
    )


# ========= Crash Reporting Tests =========
def test_crash_report_with_post(clients: ClientRegistry, monkeypatch: pytest.MonkeyPatch) -> None:
    exc_title = "The Wizard of Oz (1939)"
    exc_detail = "Toto, I've a feeling we're not in Kansas anymore."

    def raise_an_exception():
        raise RestAPIResponseGeneralException(status=500, title=exc_title, detail=exc_detail)

    monkeypatch.setattr(
        "cmk.gui.openapi.endpoints.aux_tags.load_tag_config",
        raise_an_exception,
    )
    test_data: dict[str, Any] = {
        "aux_tag_id": "aux_tag_id_1",
        "title": "aux_tag_1",
        "topic": "topic_1",
        "help": "HELP",
    }
    resp = clients.AuxTag.create(
        tag_data=test_data,
        expect_ok=False,
    )
    resp.assert_rest_api_crash()
    assert resp.json["title"] == "Internal Server Error"
    assert (
        resp.json["detail"]
        == "RestAPIResponseGeneralException: The Wizard of Oz (1939). Crash report generated. Please submit."
    )

    ext = resp.json["ext"]

    assert set(ext) == {
        "time",
        "os",
        "version",
        "edition",
        "exc_traceback",
        "core",
        "python_version",
        "python_paths",
        "id",
        "crash_type",
        "exc_type",
        "exc_value",
        "local_vars",
        "details",
    }

    details = resp.json["ext"]["details"]
    assert set(details) == {
        "rest_api_exception",
        "request_info",
        "check_mk_info",
        "crash_report_url",
    }


# ========= Accept parameter related Tests =========
def test_invalid_content_type(
    test_endpoint_accept_parameter: WrappedEndpoint,
    aut_user_auth_wsgi_app: WebTestAppForCMK,
) -> None:
    response = aut_user_auth_wsgi_app.call_method(
        "post",
        "/NO_SITE/check_mk/api/1.0/test_accept_parameter",
        "",
        {"Accept": "application/json", "content-type": "application/i-do-not-exist"},  # headers
        status=415,
    )

    assert response.json["title"] == "Content type not valid for this endpoint."
    assert (
        response.json["detail"]
        == "Content-Type 'application/i-do-not-exist' not supported for this endpoint."
    )


@pytest.mark.parametrize(
    "payload",
    [
        "",
        "I am not a .tar.gz file",
    ],
)
def test_invalid_payload(
    test_endpoint_accept_parameter: WrappedEndpoint,
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    payload: str,
) -> None:
    response = aut_user_auth_wsgi_app.call_method(
        "post",
        "/NO_SITE/check_mk/api/1.0/test_accept_parameter",
        payload,
        {"Accept": "application/json", "content-type": "application/gzip"},  # headers
        status=400,
    )

    assert response.json["title"] == "Bad Request"
    assert response.json["detail"] == "Payload is not a valid .tar.gz file"


def test_valid_gzip_file(
    test_endpoint_accept_parameter: WrappedEndpoint,
    aut_user_auth_wsgi_app: WebTestAppForCMK,
) -> None:
    payload = base64.b64decode(TEST_TARGZ_FILE)
    aut_user_auth_wsgi_app.call_method(
        "post",
        "/NO_SITE/check_mk/api/1.0/test_accept_parameter",
        payload,
        {"Accept": "application/json", "content-type": "application/gzip"},  # headers
        status=204,
    )


@pytest.mark.parametrize(
    "content_type,payload",
    [
        ("application/json", json.dumps({"permission": "granted"})),
        ("application/gzip", base64.b64decode(TEST_TARGZ_FILE)),
    ],
)
def test_endpoint_accept_multiple_types(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    test_multiple_accept_endpoint: WrappedEndpoint,
    content_type: str,
    payload: str,
) -> None:
    res = aut_user_auth_wsgi_app.call_method(
        "post",
        "/NO_SITE/check_mk/api/1.0/test_multiple_content_types",
        payload,
        {"Accept": "application/json", "Content-type": content_type},
        status=200,
    )

    assert res.json["permission"] == content_type


# ========= Authorization of reserved endpoint validation =========
def test_reserved_endpoint_auth(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    test_internal_endpoint: WrappedEndpoint,
    api_client: RestApiClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    res = aut_user_auth_wsgi_app.call_method(
        "get",
        "/NO_SITE/check_mk/api/1.0/i_am_reserved",
        "",
        {"Accept": "application/json"},
        status=401,
    )

    assert res.json["detail"] == "This endpoint is reserved for Checkmk."

    mocked_secret_path = tmp_path / "siteinternal.secret"
    mocked_secret_path.write_bytes(b"unittestsecret")
    monkeypatch.setattr(SiteInternalSecret, "path", mocked_secret_path)

    res_ = api_client.request(
        method="get",
        url="/i_am_reserved",
        headers={
            "Accept": "application/json",
            "Authorization": "InternalToken dW5pdHRlc3RzZWNyZXQ=",  # unittestsecret
        },
    )

    assert res_.status_code == 204
