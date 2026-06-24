#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

import contextlib
import dataclasses
import json
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Annotated, cast, override
from unittest.mock import MagicMock

import pytest
from pydantic import PlainSerializer
from werkzeug.datastructures import ETags, Headers

from cmk.gui.config import Config
from cmk.gui.exceptions import MKAuthException, MKUnauthenticatedException
from cmk.gui.logged_in import user
from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    ETag,
    HeaderParam,
    PathParam,
    QueryParam,
)
from cmk.gui.openapi.framework.handler import dump_body, handle_endpoint_request
from cmk.gui.openapi.framework.model import ApiOmitted
from cmk.gui.openapi.framework.model.common_fields import FieldsFilterType
from cmk.gui.openapi.framework.model.response import ApiResponse
from cmk.gui.openapi.restful_objects.validators import PermissionValidator
from cmk.gui.openapi.utils import (
    RestAPIForbiddenException,
    RestAPIHeaderValidationException,
    RestAPIPermissionException,
    RestAPIRequestGeneralException,
    RestAPIResponseException,
    RestAPIWatoDisabledException,
)
from cmk.gui.utils.permission_verification import AllPerm, Perm
from tests.unit.cmk.gui.openapi.framework.factories import (
    RawRequestDataFactory,
    RequestEndpointFactory,
)


@dataclass
class _TestResponse:
    field: int


@dataclass
class _TestResponseOmitted:
    field: int
    omitted: str | ApiOmitted = ApiOmitted()


def test_dump_response_empty() -> None:
    result = dump_body(None, None, is_testing=True)
    assert result is None


def test_dump_response_simple() -> None:
    result = dump_body(_TestResponse(field=123), _TestResponse, is_testing=True)
    assert result == b'{"field":123}'


def test_dump_response_omitted() -> None:
    result = dump_body(_TestResponseOmitted(field=123), _TestResponseOmitted, is_testing=True)
    assert result == b'{"field":123}'
    result = dump_body(
        _TestResponseOmitted(field=123, omitted="no"), _TestResponseOmitted, is_testing=True
    )
    assert result == b'{"field":123,"omitted":"no"}'


def test_dump_response_annotated() -> None:
    result = dump_body(
        _TestResponse(field=123),
        cast(type[_TestResponse], Annotated[_TestResponse, "foo"]),
        is_testing=True,
    )
    assert result == b'{"field":123}'


def test_dump_response_pydantic_annotated() -> None:
    def _serializer(value: _TestResponse) -> dict:
        # both aliasing and changing types work
        return {"custom_name": str(value.field * 2)}

    result = dump_body(
        _TestResponse(field=123),
        cast(type[_TestResponse], Annotated[_TestResponse, PlainSerializer(_serializer)]),
        is_testing=True,
    )
    assert result == b'{"custom_name":"246"}'


@dataclass
class _TestResponseB:
    name: str


type _AliasedResponseUnion = _TestResponse | _TestResponseB
type _AliasedResponseWithSerializer = Annotated[
    _TestResponse | _TestResponseB,
    PlainSerializer(lambda x: {"custom": x.field if hasattr(x, "field") else x.name}),
]


def test_dump_response_union_first_member() -> None:
    result = dump_body(_TestResponse(field=42), _TestResponse | _TestResponseB, is_testing=True)
    assert result == b'{"field":42}'


def test_dump_response_union_second_member() -> None:
    result = dump_body(
        _TestResponseB(name="hello"), _TestResponse | _TestResponseB, is_testing=True
    )
    assert result == b'{"name":"hello"}'


def test_dump_response_union_wrong_type_raises() -> None:
    with pytest.raises(ValueError, match="should be"):
        dump_body(object(), _TestResponse | _TestResponseB, is_testing=True)


def test_dump_response_type_alias_union() -> None:
    result = dump_body(_TestResponse(field=7), _AliasedResponseUnion, is_testing=True)
    assert result == b'{"field":7}'


def test_dump_response_annotated_union_uses_annotation() -> None:
    # A PlainSerializer on the Annotated wrapper must survive through resolve_type and be
    # applied by Pydantic — if the annotation were stripped the output would be {"field":...}.
    result = dump_body(_TestResponse(field=42), _AliasedResponseWithSerializer, is_testing=True)
    assert result == b'{"custom":42}'

    result = dump_body(_TestResponseB(name="hi"), _AliasedResponseWithSerializer, is_testing=True)
    assert result == b'{"custom":"hi"}'


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


def _api_context() -> ApiContext:
    return ApiContext.new(
        config=Config(),
        version=APIVersion.UNSTABLE,
        etag_if_match=ETags(),
        host_url="http://localhost/",
        user_id=None,
        token=None,
    )


def test_handle_endpoint_request_wato_disabled(permission_validator: PermissionValidator) -> None:
    request_endpoint = RequestEndpointFactory.build(doc_group="Setup")
    request_data = RawRequestDataFactory.build()
    with pytest.raises(RestAPIWatoDisabledException):
        handle_endpoint_request(
            request_endpoint,
            request_data,
            _api_context(),
            permission_validator,
            update_config_generation=lambda: None,
            do_git_commit=lambda: None,
            wato_enabled=False,
        )


def test_handle_endpoint_request_accept_required(permission_validator: PermissionValidator) -> None:
    request_endpoint = RequestEndpointFactory.build()
    request_data = RawRequestDataFactory.build(headers=Headers({}))
    with pytest.raises(RestAPIHeaderValidationException) as exc_info:
        handle_endpoint_request(
            request_endpoint,
            request_data,
            _api_context(),
            permission_validator,
            update_config_generation=lambda: None,
            do_git_commit=lambda: None,
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
        _api_context(),
        permission_validator,
        update_config_generation=lambda: None,
        do_git_commit=lambda: None,
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
    with pytest.raises(RestAPIRequestGeneralException) as exc_info:
        handle_endpoint_request(
            request_endpoint,
            request_data,
            _api_context(),
            permission_validator,
            update_config_generation=lambda: None,
            do_git_commit=lambda: None,
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
    with pytest.raises(RestAPIRequestGeneralException) as exc_info:
        handle_endpoint_request(
            request_endpoint,
            request_data,
            _api_context(),
            permission_validator,
            update_config_generation=lambda: None,
            do_git_commit=lambda: None,
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
    with pytest.raises(RestAPIRequestGeneralException) as exc_info:
        handle_endpoint_request(
            request_endpoint,
            request_data,
            _api_context(),
            permission_validator,
            update_config_generation=lambda: None,
            do_git_commit=lambda: None,
            wato_enabled=True,
            wato_use_git=False,
            is_testing=False,
        )

    response = exc_info.value.to_problem()
    assert response.status_code == 404, response.get_data(as_text=True)
    response_json = response.get_json()
    assert "path.path_param" in response_json["detail"]
    assert response_json["fields"]["path.path_param"]["type"] == "missing"


def test_handle_endpoint_request_missing_parameters_body(
    permission_validator: PermissionValidator,
) -> None:
    request_endpoint = RequestEndpointFactory.build(
        handler=_handler_body, content_type="application/json", accept="application/json"
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
    with pytest.raises(RestAPIRequestGeneralException) as exc_info:
        handle_endpoint_request(
            request_endpoint,
            request_data,
            _api_context(),
            permission_validator,
            update_config_generation=lambda: None,
            do_git_commit=lambda: None,
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
        _api_context(),
        permission_validator,
        update_config_generation=lambda: None,
        do_git_commit=lambda: None,
        wato_enabled=True,
        wato_use_git=False,
        is_testing=False,
    )

    assert response.status_code == 200, response.get_data(as_text=True)
    assert response.get_data() == b'{"body_field":123}'
    assert dict(response.headers) == {
        "Content-Type": "application/json",
        "Content-Length": "18",
    }


@pytest.mark.parametrize(
    ["wato_use_git", "expected_git_calls"],
    [(False, 0), (True, 1)],
)
def test_handle_endpoint_request_runs_config_hooks_on_write(
    permission_validator: PermissionValidator,
    wato_use_git: bool,
    expected_git_calls: int,
) -> None:
    request_endpoint = RequestEndpointFactory.build(
        method="post",
        update_config_generation=True,
    )
    request_data = RawRequestDataFactory.build(
        headers=Headers({"Accept": request_endpoint.content_type}),
    )
    update_config_generation = MagicMock()
    do_git_commit = MagicMock()

    response = handle_endpoint_request(
        request_endpoint,
        request_data,
        _api_context(),
        permission_validator,
        update_config_generation=update_config_generation,
        do_git_commit=do_git_commit,
        wato_enabled=True,
        wato_use_git=wato_use_git,
    )

    assert response.status_code == 204, response.get_data(as_text=True)
    update_config_generation.assert_called_once_with()
    assert do_git_commit.call_count == expected_git_calls


def test_handle_endpoint_request_skips_config_hooks_for_read(
    permission_validator: PermissionValidator,
) -> None:
    request_endpoint = RequestEndpointFactory.build(
        method="get",
        update_config_generation=True,
    )
    request_data = RawRequestDataFactory.build(
        headers=Headers({"Accept": request_endpoint.content_type}),
    )
    update_config_generation = MagicMock()
    do_git_commit = MagicMock()

    handle_endpoint_request(
        request_endpoint,
        request_data,
        _api_context(),
        permission_validator,
        update_config_generation=update_config_generation,
        do_git_commit=do_git_commit,
        wato_enabled=True,
        wato_use_git=True,
    )

    update_config_generation.assert_not_called()
    do_git_commit.assert_not_called()


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
        _api_context(),
        permission_validator,
        update_config_generation=lambda: None,
        do_git_commit=lambda: None,
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
            _api_context(),
            permission_validator,
            update_config_generation=lambda: None,
            do_git_commit=lambda: None,
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
            _api_context(),
            permission_validator,
            update_config_generation=lambda: None,
            do_git_commit=lambda: None,
            wato_enabled=True,
            wato_use_git=False,
            is_testing=False,
        )


def test_handle_endpoint_request_permission_denied_is_forbidden(
    permission_validator: PermissionValidator,
) -> None:
    """A failed permission check of an authenticated user must result in a 403, not a 401."""

    def _denied_handler() -> None:
        raise MKAuthException("We are sorry, but you lack the permission for this operation.")

    request_endpoint = RequestEndpointFactory.build(handler=_denied_handler)
    request_data = RawRequestDataFactory.build(
        headers=Headers({"Accept": request_endpoint.content_type})
    )
    with pytest.raises(RestAPIForbiddenException) as exc_info:
        handle_endpoint_request(
            request_endpoint,
            request_data,
            _api_context(),
            permission_validator,
            update_config_generation=lambda: None,
            do_git_commit=lambda: None,
            wato_enabled=True,
            wato_use_git=False,
            is_testing=False,
        )

    response = exc_info.value.to_problem()
    assert response.status_code == 403, response.get_data(as_text=True)
    assert "lack the permission" in response.get_json()["detail"]


def test_handle_endpoint_request_unauthenticated_stays_unauthorized(
    permission_validator: PermissionValidator,
) -> None:
    """Missing authentication must not be remapped to a 403."""

    def _unauthenticated_handler() -> None:
        raise MKUnauthenticatedException("You are not authenticated.")

    request_endpoint = RequestEndpointFactory.build(handler=_unauthenticated_handler)
    request_data = RawRequestDataFactory.build(
        headers=Headers({"Accept": request_endpoint.content_type})
    )
    with pytest.raises(MKUnauthenticatedException):
        handle_endpoint_request(
            request_endpoint,
            request_data,
            _api_context(),
            permission_validator,
            update_config_generation=lambda: None,
            do_git_commit=lambda: None,
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
        _api_context(),
        permission_validator,
        update_config_generation=lambda: None,
        do_git_commit=lambda: None,
        wato_enabled=True,
        wato_use_git=False,
        is_testing=False,
    )
    assert response.get_data() == b'{"id": "123"}'


def test_handle_endpoint_with_context(permission_validator: PermissionValidator) -> None:
    def handler(api_context: ApiContext) -> None:
        assert api_context.version == APIVersion.UNSTABLE

    request_endpoint = RequestEndpointFactory.build(handler=handler, content_type=None)
    request_data = RawRequestDataFactory.build()
    handle_endpoint_request(
        request_endpoint,
        request_data,
        _api_context(),
        permission_validator,
        update_config_generation=lambda: None,
        do_git_commit=lambda: None,
        wato_enabled=True,
        wato_use_git=False,
        is_testing=False,
    )


def test_handle_endpoint_output_etag(permission_validator: PermissionValidator) -> None:
    etag = ETag({"key": "value"})

    def handler() -> ApiResponse[None]:
        return ApiResponse(body=None, status_code=204, etag=etag)

    request_endpoint = RequestEndpointFactory.build(
        handler=handler, content_type=None, etag="output"
    )
    request_data = RawRequestDataFactory.build()
    response = handle_endpoint_request(
        request_endpoint,
        request_data,
        _api_context(),
        permission_validator,
        update_config_generation=lambda: None,
        do_git_commit=lambda: None,
        wato_enabled=True,
        wato_use_git=False,
        is_testing=False,
    )
    assert response.headers["ETag"] == f'"{etag.hash()}"'


def test_handle_endpoint_missing_etag(permission_validator: PermissionValidator) -> None:
    def handler() -> None:
        return None

    request_endpoint = RequestEndpointFactory.build(
        handler=handler, content_type=None, etag="output"
    )
    request_data = RawRequestDataFactory.build()
    with pytest.raises(RestAPIResponseException, match="ETag header expected"):
        handle_endpoint_request(
            request_endpoint,
            request_data,
            _api_context(),
            permission_validator,
            update_config_generation=lambda: None,
            do_git_commit=lambda: None,
            wato_enabled=True,
            wato_use_git=False,
            is_testing=False,
        )


@dataclass
class _RequestBodyA:
    a_field: str


@dataclass
class _RequestBodyB:
    b_field: int


type _AliasBody = _RequestBodyA | _RequestBodyB


def _handler_union_body(body: _RequestBodyA | _RequestBodyB) -> _RequestBodyA | _RequestBodyB:
    return body


def _handler_alias_body(body: _AliasBody) -> _AliasBody:
    return body


def test_handle_endpoint_request_union_body_dispatches(
    permission_validator: PermissionValidator,
) -> None:
    request_endpoint = RequestEndpointFactory.build(
        handler=_handler_union_body, content_type="application/json", accept="application/json"
    )
    for body_json, expected in [
        ({"a_field": "hello"}, b'{"a_field":"hello"}'),
        ({"b_field": 99}, b'{"b_field":99}'),
    ]:
        request_data = RawRequestDataFactory.build(
            body=json.dumps(body_json).encode(),
            headers=Headers(
                {
                    "Accept": request_endpoint.content_type,
                    "Content-Type": request_endpoint.accept,
                }
            ),
        )
        response = handle_endpoint_request(
            request_endpoint,
            request_data,
            _api_context(),
            permission_validator,
            update_config_generation=lambda: None,
            do_git_commit=lambda: None,
            wato_enabled=True,
            wato_use_git=False,
            is_testing=False,
        )
        assert response.status_code == 200, response.get_data(as_text=True)
        assert response.get_data() == expected


def test_handle_endpoint_request_type_alias_body(
    permission_validator: PermissionValidator,
) -> None:
    request_endpoint = RequestEndpointFactory.build(
        handler=_handler_alias_body, content_type="application/json", accept="application/json"
    )
    request_data = RawRequestDataFactory.build(
        body=b'{"a_field": "world"}',
        headers=Headers(
            {
                "Accept": request_endpoint.content_type,
                "Content-Type": request_endpoint.accept,
            }
        ),
    )
    response = handle_endpoint_request(
        request_endpoint,
        request_data,
        _api_context(),
        permission_validator,
        update_config_generation=lambda: None,
        do_git_commit=lambda: None,
        wato_enabled=True,
        wato_use_git=False,
        is_testing=False,
    )
    assert response.status_code == 200, response.get_data(as_text=True)
    assert response.get_data() == b'{"a_field":"world"}'
