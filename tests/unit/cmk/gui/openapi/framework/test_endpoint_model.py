#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
import inspect
import json
from collections.abc import Callable
from typing import Annotated

import pytest
from pydantic import ValidationError
from werkzeug.datastructures import Headers

from cmk.gui.openapi.framework import FromHeader, FromPath, FromQuery, RawRequestData
from cmk.gui.openapi.framework.endpoint_model import (
    _separate_parameters,
    EndpointModel,
    Parameter,
    Parameters,
    QueryParameter,
)


@dataclasses.dataclass
class _TestBody:
    int_field: int
    str_field: str


_PATH_PARAM = FromPath(description="Path parameter", example="example")
_QUERY_PARAM = FromQuery(description="Query parameter", example="example")
_QUERY_PARAM_ALIASED = FromQuery(description="Query parameter", example="example", alias="alias")
_HEADER_PARAM = FromHeader(description="Header parameter", example="example")
_HEADER_PARAM_ALIASED = FromHeader(description="Header parameter", example="example", alias="alias")


def _empty_endpoint_handler() -> None:
    raise NotImplementedError


def _body_endpoint_handler(body: _TestBody) -> None:
    raise NotImplementedError


def _path_endpoint_handler(path_param: Annotated[str, _PATH_PARAM]) -> None:
    raise NotImplementedError


def _query_endpoint_handler(query_param: Annotated[str, _QUERY_PARAM]) -> None:
    raise NotImplementedError


def _aliased_query_endpoint_handler(
    aliased_query_param: Annotated[str, _QUERY_PARAM_ALIASED],
) -> None:
    raise NotImplementedError


def _header_endpoint_handler(header_param: Annotated[str, _HEADER_PARAM]) -> None:
    raise NotImplementedError


def _aliased_header_endpoint_handler(
    aliased_header_param: Annotated[str, _HEADER_PARAM_ALIASED],
) -> None:
    raise NotImplementedError


def _return_endpoint_handler() -> _TestBody:
    raise NotImplementedError


def _all_endpoint_handler(
    body: _TestBody,
    path_param: Annotated[str, _PATH_PARAM],
    query_param: Annotated[str, _QUERY_PARAM],
    aliased_query_param: Annotated[str, _QUERY_PARAM_ALIASED],
    header_param: Annotated[str, _HEADER_PARAM],
    aliased_header_param: Annotated[str, _HEADER_PARAM_ALIASED],
) -> _TestBody:
    raise NotImplementedError


def _error_duplicate_query_endpoint_handler(
    query_param: Annotated[str, _QUERY_PARAM],
    aliased_query_param: Annotated[str, FromQuery(description="", example="", alias="query_param")],
) -> None:
    raise NotImplementedError


def _error_alias_conflict_query_endpoint_handler(
    query_param: Annotated[str, FromQuery(description="", example="", alias="aliased_query_param")],
    aliased_query_param: Annotated[str, FromQuery(description="", example="", alias="query_param")],
) -> None:
    raise NotImplementedError


def _error_duplicate_header_endpoint_handler(
    header_param: Annotated[str, _HEADER_PARAM],
    aliased_header_param: Annotated[
        str, FromHeader(description="", example="", alias="header_param")
    ],
) -> None:
    raise NotImplementedError


def _error_alias_conflict_header_endpoint_handler(
    header_param: Annotated[
        str, FromHeader(description="", example="", alias="aliased_header_param")
    ],
    aliased_header_param: Annotated[
        str, FromHeader(description="", example="", alias="header_param")
    ],
) -> None:
    raise NotImplementedError


def _error_parameter_type_endpoint_handler(positional: Annotated[str, _PATH_PARAM], /) -> None:
    raise NotImplementedError


def _error_no_annotation_endpoint_handler(who_knows) -> None:  # type: ignore[no-untyped-def]
    raise NotImplementedError


def _params(
    *,
    path: dict[str, Parameter] | None = None,
    query: dict[str, QueryParameter] | None = None,
    query_aliases: dict[str, str] | None = None,
    headers: dict[str, Parameter] | None = None,
    header_aliases: dict[str, str] | None = None,
) -> Parameters:
    return Parameters(
        path=path or {},
        query=query or {},
        query_aliases=query_aliases or {},
        headers=headers or {},
        header_aliases=header_aliases or {},
    )


@pytest.mark.parametrize(
    "func, expected",
    [
        (_empty_endpoint_handler, Parameters()),
        (_body_endpoint_handler, Parameters()),
        (
            _path_endpoint_handler,
            _params(
                path={
                    "path_param": Parameter(
                        annotation=Annotated[str, _PATH_PARAM],  # type: ignore[arg-type]
                        default=dataclasses.MISSING,
                        description="Path parameter",
                        example="example",
                    )
                }
            ),
        ),
        (
            _query_endpoint_handler,
            _params(
                query={
                    "query_param": QueryParameter(
                        annotation=Annotated[str, _QUERY_PARAM],  # type: ignore[arg-type]
                        default=dataclasses.MISSING,
                        description="Query parameter",
                        example="example",
                    )
                }
            ),
        ),
        (
            _aliased_query_endpoint_handler,
            _params(
                query={
                    "aliased_query_param": QueryParameter(
                        annotation=Annotated[str, _QUERY_PARAM_ALIASED],  # type: ignore[arg-type]
                        default=dataclasses.MISSING,
                        description="Query parameter",
                        example="example",
                    )
                },
                query_aliases={"aliased_query_param": "alias"},
            ),
        ),
        (
            _header_endpoint_handler,
            _params(
                headers={
                    "header_param": Parameter(
                        annotation=Annotated[str, _HEADER_PARAM],  # type: ignore[arg-type]
                        default=dataclasses.MISSING,
                        description="Header parameter",
                        example="example",
                    )
                }
            ),
        ),
        (
            _aliased_header_endpoint_handler,
            _params(
                headers={
                    "aliased_header_param": Parameter(
                        annotation=Annotated[str, _HEADER_PARAM_ALIASED],  # type: ignore[arg-type]
                        default=dataclasses.MISSING,
                        description="Header parameter",
                        example="example",
                    )
                },
                header_aliases={"aliased_header_param": "alias"},
            ),
        ),
        (_return_endpoint_handler, Parameters()),
        (
            _all_endpoint_handler,
            _params(
                path={
                    "path_param": Parameter(
                        annotation=Annotated[str, _PATH_PARAM],  # type: ignore[arg-type]
                        default=dataclasses.MISSING,
                        description="Path parameter",
                        example="example",
                    )
                },
                query={
                    "query_param": QueryParameter(
                        annotation=Annotated[str, _QUERY_PARAM],  # type: ignore[arg-type]
                        default=dataclasses.MISSING,
                        description="Query parameter",
                        example="example",
                    ),
                    "aliased_query_param": QueryParameter(
                        annotation=Annotated[str, _QUERY_PARAM_ALIASED],  # type: ignore[arg-type]
                        default=dataclasses.MISSING,
                        description="Query parameter",
                        example="example",
                    ),
                },
                query_aliases={"aliased_query_param": "alias"},
                headers={
                    "header_param": Parameter(
                        annotation=Annotated[str, _HEADER_PARAM],  # type: ignore[arg-type]
                        default=dataclasses.MISSING,
                        description="Header parameter",
                        example="example",
                    ),
                    "aliased_header_param": Parameter(
                        annotation=Annotated[str, _HEADER_PARAM_ALIASED],  # type: ignore[arg-type]
                        default=dataclasses.MISSING,
                        description="Header parameter",
                        example="example",
                    ),
                },
                header_aliases={"aliased_header_param": "alias"},
            ),
        ),
    ],
)
def test_parameters(func: Callable, expected: Parameters) -> None:
    signature = inspect.signature(func)
    parameters = _separate_parameters(signature)
    assert parameters == expected


@pytest.mark.parametrize(
    "func, match",
    [
        (_error_duplicate_query_endpoint_handler, "Alias conflict"),  # covered by alias check
        (_error_alias_conflict_query_endpoint_handler, "Alias conflict"),
        (_error_duplicate_header_endpoint_handler, "Alias conflict"),  # covered by alias check
        (_error_alias_conflict_header_endpoint_handler, "Alias conflict"),
        (_error_parameter_type_endpoint_handler, "Invalid parameter kind"),
        (_error_no_annotation_endpoint_handler, "Missing parameter annotation"),
    ],
)
def test_invalid_parameters(func: Callable, match: str) -> None:
    signature = inspect.signature(func)
    with pytest.raises(ValueError, match=match):
        _separate_parameters(signature)


def _request_data(
    *,
    body: dict[str, object] | None = None,
    path: dict[str, str] | None = None,
    query: dict[str, list[str]] | None = None,
    headers: dict[str, str] | None = None,
) -> RawRequestData:
    if body:
        body_bytes = json.dumps(body).encode("utf-8")
    else:
        body_bytes = None
    return {
        "body": body_bytes,
        "path": path or {},
        "query": query or {},
        "headers": Headers(headers),
    }


@pytest.mark.parametrize(
    "func, request_data",
    [
        (_empty_endpoint_handler, _request_data()),
        (_body_endpoint_handler, _request_data(body={"int_field": 1, "str_field": "test"})),
        (_path_endpoint_handler, _request_data(path={"path_param": "test"})),
        (_query_endpoint_handler, _request_data(query={"query_param": ["test"]})),
        (_aliased_query_endpoint_handler, _request_data(query={"alias": ["test"]})),
        (_header_endpoint_handler, _request_data(headers={"header_param": "test"})),
        (_aliased_header_endpoint_handler, _request_data(headers={"alias": "test"})),
        (_return_endpoint_handler, _request_data()),
        (
            _all_endpoint_handler,
            _request_data(
                body={"int_field": 1, "str_field": "test"},
                path={"path_param": "test"},
                query={"query_param": ["test"], "alias": ["test"]},
                headers={"header_param": "test", "alias": "test"},
            ),
        ),
    ],
)
def test_input_model_validate_parameters(func: Callable, request_data: RawRequestData) -> None:
    model = EndpointModel.build(func)
    model._validate_request_parameters(
        request_data, "application/json" if request_data["body"] else None
    )


def test_input_model_extra_body() -> None:
    """Test that specifying a body when none is expected raises an error."""
    model = EndpointModel.build(_empty_endpoint_handler)
    with pytest.raises(ValidationError, match="type=none_required"):
        model._validate_request_parameters(_request_data(body={"extra_body_field": "test"}), None)


@pytest.mark.parametrize(
    "func, request_data",
    [
        (_empty_endpoint_handler, _request_data(path={"extra_path_field": "test"})),
        (_empty_endpoint_handler, _request_data(query={"extra_query_field": ["test"]})),
        (
            _all_endpoint_handler,
            _request_data(
                body={"int_field": 1, "str_field": "test", "extra_body_field": "test"},
                path={"path_param": "test"},
                query={"query_param": ["test"], "alias": ["test"]},
                headers={"header_param": "test", "alias": "test"},
            ),
        ),
        (
            _all_endpoint_handler,
            _request_data(
                body={"int_field": 1, "str_field": "test"},
                path={"path_param": "test", "extra_path_field": "test"},
                query={"query_param": ["test"], "alias": ["test"]},
                headers={"header_param": "test", "alias": "test"},
            ),
        ),
        (
            _all_endpoint_handler,
            _request_data(
                body={"int_field": 1, "str_field": "test"},
                path={"path_param": "test"},
                query={"query_param": ["test"], "alias": ["test"], "extra_query_field": ["test"]},
                headers={"header_param": "test", "alias": "test"},
            ),
        ),
    ],
)
def test_input_model_extra_fields(func: Callable, request_data: RawRequestData) -> None:
    model = EndpointModel.build(func)
    # type=unexpected_keyword_argument happens only because we use dataclasses (with extra=forbid)
    with pytest.raises(ValidationError, match="type=unexpected_keyword_argument"):
        model._validate_request_parameters(
            request_data, "application/json" if request_data["body"] else None
        )


@pytest.mark.parametrize(
    "request_data",
    [
        _request_data(
            body={"int_field": 1},
            path={"path_param": "test"},
            query={"query_param": ["test"], "alias": ["test"]},
            headers={"header_param": "test", "alias": "test"},
        ),
        _request_data(
            body={"int_field": 1, "str_field": "test"},
            query={"query_param": ["test"], "alias": ["test"]},
            headers={"header_param": "test", "alias": "test"},
        ),
        _request_data(
            body={"int_field": 1, "str_field": "test"},
            path={"path_param": "test"},
            headers={"header_param": "test", "alias": "test"},
        ),
        _request_data(
            body={"int_field": 1, "str_field": "test"},
            path={"path_param": "test"},
            query={"query_param": ["test"], "alias": ["test"]},
        ),
    ],
)
def test_input_model_missing_fields(request_data: RawRequestData) -> None:
    model = EndpointModel.build(_all_endpoint_handler)
    with pytest.raises(ValidationError, match="type=missing"):
        model._validate_request_parameters(request_data, "application/json")


def test_query_parameter_list() -> None:
    def _query_list_test(
        query_param: Annotated[list[str], FromQuery(description="", example="", is_list=True)],
    ) -> None:
        raise NotImplementedError

    model = EndpointModel.build(_query_list_test)
    request_data = _request_data(
        query={
            "query_param": ["test1", "test2"],
        }
    )
    bound = model._validate_request_parameters(request_data, None)
    assert bound.arguments["query_param"] == ["test1", "test2"]


def test_query_parameter_single() -> None:
    model = EndpointModel.build(_query_endpoint_handler)
    request_data = _request_data(
        query={
            "query_param": ["test1", "test2"],
        }
    )
    with pytest.raises(ValidationError, match="must be specified only once.*type=value_error"):
        model._validate_request_parameters(request_data, None)
