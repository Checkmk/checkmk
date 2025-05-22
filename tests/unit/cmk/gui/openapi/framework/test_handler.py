#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import contextlib
import dataclasses
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Annotated, cast, override

import pytest
from pydantic import PlainSerializer
from werkzeug.datastructures import Headers

from tests.unit.cmk.gui.openapi.framework.factories import (
    RawRequestDataFactory,
    RequestEndpointFactory,
)

from cmk.gui.logged_in import user
from cmk.gui.openapi.framework import ApiContext, APIVersion, HeaderParam, PathParam, QueryParam
from cmk.gui.openapi.framework.handler import _dump_response, handle_endpoint_request
from cmk.gui.openapi.framework.model import ApiOmitted
from cmk.gui.openapi.framework.model.common_fields import FieldsFilterType
from cmk.gui.openapi.restful_objects.validators import PermissionValidator
from cmk.gui.openapi.utils import (
    RestAPIHeaderValidationException,
    RestAPIPermissionException,
    RestAPIRequestDataValidationException,
    RestAPIWatoDisabledException,
)
from cmk.gui.utils.permission_verification import AllPerm, Perm


@dataclass
class _TestResponse:
    field: int


@dataclass
class _TestResponseOmitted:
    field: int
    omitted: str | ApiOmitted = ApiOmitted()


def test_dump_response_empty() -> None:
    result = _dump_response(None, None, is_testing=True)
    assert result is None


def test_dump_response_simple() -> None:
    result = _dump_response(_TestResponse(field=123), _TestResponse, is_testing=True)
    assert result == b'{"field":123}'


def test_dump_response_omitted() -> None:
    result = _dump_response(_TestResponseOmitted(field=123), _TestResponseOmitted, is_testing=True)
    assert result == b'{"field":123}'
    result = _dump_response(
        _TestResponseOmitted(field=123, omitted="no"), _TestResponseOmitted, is_testing=True
    )
    assert result == b'{"field":123,"omitted":"no"}'


def test_dump_response_annotated() -> None:
    result = _dump_response(
        _TestResponse(field=123),
        cast(type[_TestResponse], Annotated[_TestResponse, "foo"]),
        is_testing=True,
    )
    assert result == b'{"field":123}'


def test_dump_response_pydantic_annotated() -> None:
    def _serializer(value: _TestResponse) -> dict:
        # both aliasing and changing types work
        return {"custom_name": str(value.field * 2)}

    result = _dump_response(
        _TestResponse(field=123),
        cast(type[_TestResponse], Annotated[_TestResponse, PlainSerializer(_serializer)]),
        is_testing=True,
    )
    assert result == b'{"custom_name":"246"}'


class _DummyPermissionValidator(PermissionValidator):
    """Doesn't enable permission tracking, thus not requiring a GUI context."""

    @override
    @contextlib.contextmanager
    def track_permissions(self) -> Iterator[None]:
        yield None


@pytest.fixture(name="permission_validator")
def fixture_permission_validator() -> PermissionValidator:
    return _DummyPermissionValidator(_on_permission_checked=lambda _: None)


@dataclasses.dataclass
class _Schema:
    body_field: int


def _handler(
    body: _Schema,
    path_param: Annotated[int, PathParam(description="Path parameter", example="123")],
    query_param: Annotated[str, QueryParam(description="Query parameter", example="foo")],
    aliased_query_param: Annotated[
        list[int],
        QueryParam(
            description="Aliased query parameter", example="456", alias="aliased", is_list=True
        ),
    ],
    header_param: Annotated[str, HeaderParam(description="Header parameter", example="baz")],
    aliased_header_param: Annotated[
        int,
        HeaderParam(description="Aliased header parameter", example="789", alias="aliased-header"),
    ],
) -> _Schema:
    assert isinstance(body, _Schema)
    assert isinstance(path_param, int)
    assert isinstance(query_param, str)
    assert isinstance(aliased_query_param, list)
    assert len(aliased_query_param) >= 1
    assert all(isinstance(i, int) for i in aliased_query_param)
    assert isinstance(header_param, str)
    assert isinstance(aliased_header_param, int)
    return body


def _handler_body(body: _Schema) -> _Schema:
    assert isinstance(body, _Schema)
    return body


def _handler_path(
    path_param: Annotated[int, PathParam(description="Path parameter", example="123")],
) -> None:
    assert isinstance(path_param, int)


def _handler_query(
    query_param: Annotated[str, QueryParam(description="Query parameter", example="foo")],
    aliased_query_param: Annotated[
        list[int],
        QueryParam(
            description="Aliased query parameter", example="456", alias="aliased", is_list=True
        ),
    ],
) -> None:
    assert isinstance(query_param, str)
    assert isinstance(aliased_query_param, list)
    assert len(aliased_query_param) >= 1
    assert all(isinstance(i, int) for i in aliased_query_param)


def _handler_header(
    header_param: Annotated[str, HeaderParam(description="Header parameter", example="baz")],
    aliased_header_param: Annotated[
        int,
        HeaderParam(description="Aliased header parameter", example="789", alias="aliased-header"),
    ],
) -> None:
    assert isinstance(header_param, str)
    assert isinstance(aliased_header_param, int)


def test_handle_endpoint_request_wato_disabled(permission_validator: PermissionValidator) -> None:
    request_endpoint = RequestEndpointFactory.build(doc_group="Setup")
    request_data = RawRequestDataFactory.build()
    with pytest.raises(RestAPIWatoDisabledException):
        handle_endpoint_request(
            request_endpoint,
            request_data,
            ApiContext(version=APIVersion.UNSTABLE),
            permission_validator,
            wato_enabled=False,
        )


def test_handle_endpoint_request_accept_required(permission_validator: PermissionValidator) -> None:
    request_endpoint = RequestEndpointFactory.build()
    request_data = RawRequestDataFactory.build(headers=Headers({}))
    with pytest.raises(RestAPIHeaderValidationException) as exc_info:
        handle_endpoint_request(
            request_endpoint,
            request_data,
            ApiContext(version=APIVersion.UNSTABLE),
            permission_validator,
        )

    assert "Accept Header" in exc_info.value.detail


def test_handle_endpoint_request_empty_handler(permission_validator: PermissionValidator) -> None:
    def _empty_handler() -> None:
        return None

    request_endpoint = RequestEndpointFactory.build(handler=_empty_handler)
    request_data = RawRequestDataFactory.build(
        headers=Headers({"Accept": request_endpoint.content_type}),
    )
    response = handle_endpoint_request(
        request_endpoint,
        request_data,
        ApiContext(version=APIVersion.UNSTABLE),
        permission_validator,
        wato_enabled=True,
        wato_use_git=False,
        is_testing=False,
    )

    assert response.status_code == 204, response.get_data(as_text=True)
    assert response.get_data() == b""
    assert dict(response.headers) == {}


def test_handle_endpoint_request_missing_parameters_header(
    permission_validator: PermissionValidator,
) -> None:
    request_endpoint = RequestEndpointFactory.build(
        handler=_handler_header, content_type="application/json"
    )
    request_data = RawRequestDataFactory.build(
        headers=Headers({"Accept": request_endpoint.content_type}),
    )
    with pytest.raises(RestAPIRequestDataValidationException) as exc_info:
        handle_endpoint_request(
            request_endpoint,
            request_data,
            ApiContext(version=APIVersion.UNSTABLE),
            permission_validator,
            wato_enabled=True,
            wato_use_git=False,
            is_testing=False,
        )

    response = exc_info.value.to_problem()
    assert response.status_code == 400, response.get_data(as_text=True)
    response_json = response.get_json()
    assert "headers.header_param" in response_json["detail"]
    assert response_json["fields"]["headers.header_param"]["type"] == "missing"
    assert "headers.aliased-header" in response_json["detail"]
    assert response_json["fields"]["headers.aliased-header"]["type"] == "missing"


def test_handle_endpoint_request_missing_parameters_query(
    permission_validator: PermissionValidator,
) -> None:
    request_endpoint = RequestEndpointFactory.build(
        handler=_handler_query, content_type="application/json"
    )
    request_data = RawRequestDataFactory.build(
        headers=Headers({"Accept": request_endpoint.content_type}), query={}
    )
    with pytest.raises(RestAPIRequestDataValidationException) as exc_info:
        handle_endpoint_request(
            request_endpoint,
            request_data,
            ApiContext(version=APIVersion.UNSTABLE),
            permission_validator,
            wato_enabled=True,
            wato_use_git=False,
            is_testing=False,
        )

    response = exc_info.value.to_problem()
    assert response.status_code == 400, response.get_data(as_text=True)
    response_json = response.get_json()
    assert "query.query_param" in response_json["detail"]
    assert response_json["fields"]["query.query_param"]["type"] == "missing"
    assert "query.aliased" in response_json["detail"]
    assert response_json["fields"]["query.aliased"]["type"] == "missing"


def test_handle_endpoint_request_missing_parameters_path(
    permission_validator: PermissionValidator,
) -> None:
    request_endpoint = RequestEndpointFactory.build(
        handler=_handler_path, content_type="application/json"
    )
    request_data = RawRequestDataFactory.build(
        headers=Headers({"Accept": request_endpoint.content_type}), path={}
    )
    with pytest.raises(RestAPIRequestDataValidationException) as exc_info:
        handle_endpoint_request(
            request_endpoint,
            request_data,
            ApiContext(version=APIVersion.UNSTABLE),
            permission_validator,
            wato_enabled=True,
            wato_use_git=False,
            is_testing=False,
        )

    response = exc_info.value.to_problem()
    assert response.status_code == 400, response.get_data(as_text=True)
    response_json = response.get_json()
    assert "path.path_param" in response_json["detail"]
    assert response_json["fields"]["path.path_param"]["type"] == "missing"


def test_handle_endpoint_request_missing_parameters_body(
    permission_validator: PermissionValidator,
) -> None:
    request_endpoint = RequestEndpointFactory.build(
        handler=_handler, content_type="application/json", accept="application/json"
    )
    request_data = RawRequestDataFactory.build(
        body=b"{}",
        headers=Headers(
            {
                "Accept": request_endpoint.content_type,
                "Content-Type": request_endpoint.accept,
            }
        ),
    )
    with pytest.raises(RestAPIRequestDataValidationException) as exc_info:
        handle_endpoint_request(
            request_endpoint,
            request_data,
            ApiContext(version=APIVersion.UNSTABLE),
            permission_validator,
            wato_enabled=True,
            wato_use_git=False,
            is_testing=False,
        )

    response = exc_info.value.to_problem()
    assert response.status_code == 400, response.get_data(as_text=True)
    response_json = response.get_json()
    assert "body.body_field" in response_json["detail"]
    assert response_json["fields"]["body.body_field"]["type"] == "missing"


def test_handle_endpoint_request_complex_handler(
    permission_validator: PermissionValidator,
) -> None:
    request_endpoint = RequestEndpointFactory.build(
        handler=_handler, content_type="application/json", accept="application/json", etag=None
    )
    request_data = RawRequestDataFactory.build(
        body=b'{"body_field": 123}',
        headers=Headers(
            {
                "Accept": request_endpoint.content_type,
                "Content-Type": request_endpoint.accept,
                "Header_Param": RawRequestDataFactory.__faker__.sentence(),
                "Aliased-Header": str(RawRequestDataFactory.__faker__.random_number()),
            }
        ),
        query={
            "query_param": [RawRequestDataFactory.__faker__.word()],
            "aliased": [str(RawRequestDataFactory.__faker__.random_number())],
        },
        path={
            "path_param": str(RawRequestDataFactory.__faker__.random_number()),
        },
    )
    response = handle_endpoint_request(
        request_endpoint,
        request_data,
        ApiContext(version=APIVersion.UNSTABLE),
        permission_validator,
        wato_enabled=True,
        wato_use_git=False,
        is_testing=False,
    )

    assert response.status_code == 200, response.get_data(as_text=True)
    assert response.get_data() == b'{"body_field": 123}'
    assert dict(response.headers) == {
        "Content-Type": "application/json",
        "Content-Length": "19",
    }


def _handler_permission_check() -> None:
    user.need_permission("wato.edit")


@pytest.mark.usefixtures("request_context", "with_admin_login")
def test_handle_endpoint_request_permissions() -> None:
    request_endpoint = RequestEndpointFactory.build(
        handler=_handler_permission_check, permissions_required=Perm("wato.edit")
    )
    permission_validator = PermissionValidator.create(
        request_endpoint.permissions_required, "<endpoint>", is_testing=False
    )
    request_data = RawRequestDataFactory.build(
        headers=Headers({"Accept": request_endpoint.content_type})
    )
    response = handle_endpoint_request(
        request_endpoint,
        request_data,
        ApiContext(version=APIVersion.UNSTABLE),
        permission_validator,
        wato_enabled=True,
        wato_use_git=False,
        is_testing=False,
    )
    assert response.status_code == 204, response.get_data(as_text=True)


@pytest.mark.usefixtures("request_context", "with_admin_login")
def test_handle_endpoint_request_permissions_not_declared() -> None:
    request_endpoint = RequestEndpointFactory.build(
        handler=_handler_permission_check,
        permissions_required=None,
    )
    # this is only checked in testing mode
    permission_validator = PermissionValidator.create(
        request_endpoint.permissions_required, "<endpoint>", is_testing=True
    )
    request_data = RawRequestDataFactory.build(
        headers=Headers({"Accept": request_endpoint.content_type})
    )
    with pytest.raises(RestAPIPermissionException):
        handle_endpoint_request(
            request_endpoint,
            request_data,
            ApiContext(version=APIVersion.UNSTABLE),
            permission_validator,
            wato_enabled=True,
            wato_use_git=False,
            is_testing=True,
        )


@pytest.mark.usefixtures("request_context", "with_admin_login")
def test_handle_endpoint_request_permissions_not_checked() -> None:
    request_endpoint = RequestEndpointFactory.build(
        handler=_handler_permission_check,
        permissions_required=AllPerm([Perm("wato.edit"), Perm("wato.users")]),
    )
    permission_validator = PermissionValidator.create(
        request_endpoint.permissions_required, "<endpoint>", is_testing=False
    )
    request_data = RawRequestDataFactory.build(
        headers=Headers({"Accept": request_endpoint.content_type})
    )
    with pytest.raises(RestAPIPermissionException):
        handle_endpoint_request(
            request_endpoint,
            request_data,
            ApiContext(version=APIVersion.UNSTABLE),
            permission_validator,
            wato_enabled=True,
            wato_use_git=False,
            is_testing=False,
        )


def test_handle_endpoint_with_fields_filter(permission_validator: PermissionValidator) -> None:
    @dataclass
    class _Schema:
        id: str
        field: str

    def _handler(
        body: _Schema,
        fields: FieldsFilterType,
    ) -> _Schema:
        return body

    request_endpoint = RequestEndpointFactory.build(
        handler=_handler, content_type="application/json", accept="application/json"
    )
    request_data = RawRequestDataFactory.build(
        body=b'{"id": "123", "field": "value"}',
        query={"fields": ["(id)"]},
        headers=Headers(
            {"Accept": request_endpoint.content_type, "Content-Type": request_endpoint.accept}
        ),
    )
    response = handle_endpoint_request(
        request_endpoint,
        request_data,
        ApiContext(version=APIVersion.UNSTABLE),
        permission_validator,
        wato_enabled=True,
        wato_use_git=False,
        is_testing=False,
    )
    assert response.get_data() == b'{"id": "123"}'


def test_handle_endpoint_with_context(permission_validator: PermissionValidator) -> None:
    def handler(api_context: ApiContext) -> None:
        assert api_context.version == APIVersion.UNSTABLE

    request_endpoint = RequestEndpointFactory.build(handler=handler)
    request_data = RawRequestDataFactory.build(
        headers=Headers({"Accept": request_endpoint.content_type}),
    )
    handle_endpoint_request(
        request_endpoint,
        request_data,
        ApiContext(version=APIVersion.UNSTABLE),
        permission_validator,
        wato_enabled=True,
        wato_use_git=False,
        is_testing=False,
    )
