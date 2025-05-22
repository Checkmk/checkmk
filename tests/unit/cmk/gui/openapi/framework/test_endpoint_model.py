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
from pydantic import AfterValidator, ValidationError
from werkzeug.datastructures import Headers

from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    HeaderParam,
    PathParam,
    QueryParam,
    RawRequestData,
)
from cmk.gui.openapi.framework._validation import ParameterValidator
from cmk.gui.openapi.framework.endpoint_model import (
    _QueryParameter,
    EndpointModel,
    Parameter,
    Parameters,
    SignatureParametersProcessor,
)
from cmk.gui.openapi.framework.model import ApiOmitted
from cmk.gui.openapi.framework.model.response import TypedResponse


@dataclasses.dataclass
class _TestBody:
    int_field: int
    str_field: str


_PATH_PARAM = PathParam(description="Path parameter", example="example")
_QUERY_PARAM = QueryParam(description="Query parameter", example="example")
_QUERY_PARAM_ALIASED = QueryParam(description="Query parameter", example="example", alias="alias")
_QUERY_PARAM_LIST = QueryParam(description="Query parameter", example='["example"]', is_list=True)
_HEADER_PARAM = HeaderParam(description="Header parameter", example="example")
_HEADER_PARAM_ALIASED = HeaderParam(
    description="Header parameter", example="example", alias="alias"
)


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


def _query_list_endpoint_handler(query_param: Annotated[list[str], _QUERY_PARAM_LIST]) -> None:
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


@pytest.mark.parametrize(
    "func, expected",
    [
        (_empty_endpoint_handler, Parameters()),
        (_body_endpoint_handler, Parameters()),
        (
            _path_endpoint_handler,
            Parameters(
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
            Parameters(
                query={
                    "query_param": _QueryParameter(
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
            Parameters(
                query={
                    "aliased_query_param": _QueryParameter(
                        annotation=Annotated[str, _QUERY_PARAM_ALIASED],  # type: ignore[arg-type]
                        default=dataclasses.MISSING,
                        description="Query parameter",
                        example="example",
                        alias="alias",
                    )
                },
            ),
        ),
        (
            _query_list_endpoint_handler,
            Parameters(
                query={
                    "query_param": _QueryParameter(
                        annotation=Annotated[list[str], _QUERY_PARAM_LIST],  # type: ignore[arg-type]
                        default=dataclasses.MISSING,
                        description="Query parameter",
                        example='["example"]',
                        is_list=True,
                    )
                }
            ),
        ),
        (
            _header_endpoint_handler,
            Parameters(
                headers={
                    "header_param": Parameter(
                        annotation=Annotated[str, _HEADER_PARAM],  # type: ignore[arg-type]
                        default=dataclasses.MISSING,
                        description="Header parameter",
                        example="example",
                        alias="header_param",
                    )
                }
            ),
        ),
        (
            _aliased_header_endpoint_handler,
            Parameters(
                headers={
                    "aliased_header_param": Parameter(
                        annotation=Annotated[str, _HEADER_PARAM_ALIASED],  # type: ignore[arg-type]
                        default=dataclasses.MISSING,
                        description="Header parameter",
                        example="example",
                        alias="alias",
                    )
                },
            ),
        ),
        (_return_endpoint_handler, Parameters()),
        (
            _all_endpoint_handler,
            Parameters(
                path={
                    "path_param": Parameter(
                        annotation=Annotated[str, _PATH_PARAM],  # type: ignore[arg-type]
                        default=dataclasses.MISSING,
                        description="Path parameter",
                        example="example",
                    )
                },
                query={
                    "query_param": _QueryParameter(
                        annotation=Annotated[str, _QUERY_PARAM],  # type: ignore[arg-type]
                        default=dataclasses.MISSING,
                        description="Query parameter",
                        example="example",
                    ),
                    "aliased_query_param": _QueryParameter(
                        annotation=Annotated[str, _QUERY_PARAM_ALIASED],  # type: ignore[arg-type]
                        default=dataclasses.MISSING,
                        description="Query parameter",
                        example="example",
                        alias="alias",
                    ),
                },
                headers={
                    "header_param": Parameter(
                        annotation=Annotated[str, _HEADER_PARAM],  # type: ignore[arg-type]
                        default=dataclasses.MISSING,
                        description="Header parameter",
                        example="example",
                        alias="header_param",
                    ),
                    "aliased_header_param": Parameter(
                        annotation=Annotated[str, _HEADER_PARAM_ALIASED],  # type: ignore[arg-type]
                        default=dataclasses.MISSING,
                        description="Header parameter",
                        example="example",
                        alias="alias",
                    ),
                },
            ),
        ),
    ],
)
def test_parameters(func: Callable, expected: Parameters) -> None:
    signature = inspect.signature(func)
    annotated_params = SignatureParametersProcessor.extract_annotated_parameters(signature)
    ParameterValidator.validate_parsed_parameters(annotated_params)
    parameters = SignatureParametersProcessor.parse_parameters(annotated_params)
    assert parameters == expected


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
        request_data,
        "application/json" if request_data["body"] else None,
        ApiContext(version=APIVersion.UNSTABLE),
    )


def test_input_model_extra_body() -> None:
    """Test that specifying a body when none is expected raises an error."""
    model = EndpointModel.build(_empty_endpoint_handler)
    with pytest.raises(ValidationError, match="type=none_required"):
        model._validate_request_parameters(
            _request_data(body={"extra_body_field": "test"}),
            None,
            ApiContext(version=APIVersion.UNSTABLE),
        )


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
            request_data,
            "application/json" if request_data["body"] else None,
            ApiContext(version=APIVersion.UNSTABLE),
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
        model._validate_request_parameters(
            request_data, "application/json", ApiContext(version=APIVersion.UNSTABLE)
        )


class TestAnnotatedValidators:
    @staticmethod
    def validate_one(value: str) -> str:
        if value != "one":
            raise ValueError("Value must be 'one'")
        return value

    @staticmethod
    def validate_two(value: str) -> str:
        if value != "two":
            raise ValueError("Value must be 'two'")
        return value

    @staticmethod
    def change_value(value: str) -> None:
        return None

    def test_multiple_annotated_validators(self) -> None:
        @dataclasses.dataclass
        class Body:
            field: Annotated[
                str,
                AfterValidator(TestAnnotatedValidators.validate_one),
                AfterValidator(TestAnnotatedValidators.validate_two),
            ]

        def handler(body: Body) -> None:
            return None

        model = EndpointModel.build(handler)
        with pytest.raises(ValidationError, match="Value must be 'two'"):
            model._validate_request_parameters(
                _request_data(body={"field": "one"}),
                "application/json",
                ApiContext(version=APIVersion.UNSTABLE),
            )

        with pytest.raises(ValidationError, match="Value must be 'one'"):
            model._validate_request_parameters(
                _request_data(body={"field": "three"}),
                "application/json",
                ApiContext(version=APIVersion.UNSTABLE),
            )

    def test_annotated_validator_change_value(self) -> None:
        @dataclasses.dataclass
        class Body:
            field: Annotated[str, AfterValidator(TestAnnotatedValidators.change_value)]

        def handler(body: Body) -> None:
            return None

        model = EndpointModel.build(handler)
        request_data = _request_data(body={"field": "one"})
        bound = model._validate_request_parameters(
            request_data, "application/json", ApiContext(version=APIVersion.UNSTABLE)
        )
        assert bound.arguments["body"].field is None

    def test_annotated_validator_with_different_return_values(self) -> None:
        @dataclasses.dataclass
        class Body:
            field: Annotated[
                str,
                AfterValidator(TestAnnotatedValidators.validate_one),
                AfterValidator(TestAnnotatedValidators.change_value),
            ]

        def handler(body: Body) -> None:
            return None

        model = EndpointModel.build(handler)
        request_data = _request_data(body={"field": "one"})
        bound = model._validate_request_parameters(
            request_data, "application/json", ApiContext(version=APIVersion.UNSTABLE)
        )
        assert bound.arguments["body"].field is None

    def test_annotated_validator_with_changing_value_first(self) -> None:
        @dataclasses.dataclass
        class Body:
            field: Annotated[
                str,
                AfterValidator(TestAnnotatedValidators.change_value),
                AfterValidator(TestAnnotatedValidators.validate_one),
            ]

        def handler(body: Body) -> None:
            return None

        model = EndpointModel.build(handler)
        request_data = _request_data(body={"field": "one"})
        with pytest.raises(ValidationError, match="Value must be 'one'"):
            model._validate_request_parameters(
                request_data, "application/json", ApiContext(version=APIVersion.UNSTABLE)
            )

    def test_annotated_validator_ignores_other_union_types(self) -> None:
        def handler(
            _arg: Annotated[
                Annotated[str, AfterValidator(TestAnnotatedValidators.validate_one)] | ApiOmitted,
                QueryParam(description="...", example="..."),
            ] = ApiOmitted(),
        ) -> None:
            return None

        model = EndpointModel.build(handler)

        request_data = _request_data(query={"_arg": ["one"]})
        bound = model._validate_request_parameters(
            request_data, None, ApiContext(version=APIVersion.UNSTABLE)
        )
        assert bound.arguments["_arg"] == "one"

        request_data = _request_data()
        bound = model._validate_request_parameters(
            request_data, None, ApiContext(version=APIVersion.UNSTABLE)
        )
        assert isinstance(bound.arguments["_arg"], ApiOmitted)


def test_query_parameter_list() -> None:
    model = EndpointModel.build(_query_list_endpoint_handler)
    request_data = _request_data(
        query={
            "query_param": ["test1", "test2"],
        }
    )
    bound = model._validate_request_parameters(
        request_data, None, ApiContext(version=APIVersion.UNSTABLE)
    )
    assert bound.arguments["query_param"] == ["test1", "test2"]


def test_query_parameter_single() -> None:
    model = EndpointModel.build(_query_endpoint_handler)
    request_data = _request_data(
        query={
            "query_param": ["test1", "test2"],
        }
    )
    # TODO: check if we can improve the error message here without exiting validation early
    with pytest.raises(ValidationError, match="type=string_type"):
        model._validate_request_parameters(
            request_data, None, ApiContext(version=APIVersion.UNSTABLE)
        )


def test_header_parameter_case() -> None:
    def _header_case_test(
        Header: Annotated[str, HeaderParam(description="", example="")],
    ) -> None:
        raise NotImplementedError

    model = EndpointModel.build(_header_case_test)
    request_data = _request_data(headers={"header": "test"})
    bound = model._validate_request_parameters(
        request_data, None, ApiContext(version=APIVersion.UNSTABLE)
    )
    assert bound.arguments["Header"] == "test"


def test_typed_response() -> None:
    def _handler() -> TypedResponse[_TestBody]:
        raise NotImplementedError

    model = EndpointModel.build(_handler)
    assert model.response_body_type is _TestBody
