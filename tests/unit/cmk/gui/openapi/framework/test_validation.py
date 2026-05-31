#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="type-arg"

import inspect
from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated, Literal

import pytest
from pydantic import Discriminator

from cmk.gui.openapi.framework import (
    HandlerFunction,
    HeaderParam,
    PathParam,
    QueryParam,
    validate_endpoint_definition,
)
from cmk.gui.openapi.framework._validation import ParameterValidator
from cmk.gui.openapi.framework.endpoint_model import SignatureParametersProcessor
from tests.unit.cmk.gui.openapi.framework.factories import EndpointDefinitionFactory


def _handler_error_query_duplicate(
    _query: Annotated[str, QueryParam(description="", example="")],
    _aliased_query: Annotated[str, QueryParam(description="", example="", alias="_query")],
) -> None:
    raise NotImplementedError


def _handler_error_query_alias_conflict(
    _query: Annotated[str, QueryParam(description="", example="", alias="_other")],
    _other: Annotated[str, QueryParam(description="", example="", alias="_query")],
) -> None:
    raise NotImplementedError


def _handler_error_query_duplicate_alias(
    _query: Annotated[str, QueryParam(description="", example="", alias="foo")],
    _other: Annotated[str, QueryParam(description="", example="", alias="foo")],
) -> None:
    raise NotImplementedError


def _handler_error_query_is_list_requires_list(
    _arg: Annotated[str, QueryParam(description="...", example="...", is_list=True)],
) -> None:
    raise NotImplementedError


def _handler_error_header_duplicate(
    _header: Annotated[str, HeaderParam(description="", example="")],
    _aliased_header: Annotated[str, HeaderParam(description="", example="", alias="_header")],
) -> None:
    raise NotImplementedError


def _handler_error_header_alias_conflict(
    _header: Annotated[str, HeaderParam(description="", example="", alias="_other")],
    _other: Annotated[str, HeaderParam(description="", example="", alias="_header")],
) -> None:
    raise NotImplementedError


def _handler_error_header_duplicate_alias(
    _header: Annotated[str, HeaderParam(description="", example="", alias="foo")],
    _other: Annotated[str, HeaderParam(description="", example="", alias="foo")],
) -> None:
    raise NotImplementedError


def _handler_error_header_same_name(
    _header: Annotated[str, HeaderParam(description="", example="")],
    _Header: Annotated[str, HeaderParam(description="", example="")],
) -> None:
    raise NotImplementedError


def _handler_error_parameter_kind(
    _positional: Annotated[str, PathParam(description="", example="")], /
) -> None:
    raise NotImplementedError


def _handler_error_no_annotation(_who_knows) -> None:  # type: ignore[no-untyped-def]
    raise NotImplementedError


@pytest.mark.parametrize(
    "func, match",
    [
        (_handler_error_query_duplicate, "Alias conflict"),  # covered by alias check
        (_handler_error_query_alias_conflict, "Alias conflict"),
        (_handler_error_query_duplicate_alias, "Duplicate alias"),
        (_handler_error_query_is_list_requires_list, "'_arg'.*type is not a list"),
        (_handler_error_header_duplicate, "Alias conflict"),  # covered by alias check
        (_handler_error_header_alias_conflict, "Alias conflict"),
        (_handler_error_header_duplicate_alias, "Duplicate alias"),
        (_handler_error_header_same_name, "Duplicate header parameter"),
        (_handler_error_parameter_kind, "Invalid parameter kind"),
        (_handler_error_no_annotation, "Missing parameter annotation"),
    ],
)
def test_invalid_parameters(func: Callable, match: str) -> None:
    signature = inspect.signature(func)
    annotated_params = SignatureParametersProcessor.extract_annotated_parameters(signature)
    with pytest.raises(ValueError, match=match):
        ParameterValidator.validate_parsed_parameters(annotated_params)


def test_query_is_list_supports_other_lists() -> None:
    class CustomList(list):
        pass

    def handler(
        _arg: Annotated[CustomList, QueryParam(description="...", example="...", is_list=True)],
    ) -> None:
        pass

    signature = inspect.signature(handler)
    parameters = SignatureParametersProcessor.extract_annotated_parameters(signature)
    ParameterValidator.validate_parsed_parameters(parameters)


def test_query_is_list_supports_optional_list() -> None:
    # Annotated[list[...], metadata] | None produces typing.Union (not types.UnionType),
    # because the | operator on Annotated aliases goes through typing._AnnotatedAlias.__or__.
    def handler(
        _arg: Annotated[
            Annotated[list[str], "validator"] | None,
            QueryParam(description="...", example="...", is_list=True),
        ] = None,
    ) -> None:
        pass

    signature = inspect.signature(handler)
    parameters = SignatureParametersProcessor.extract_annotated_parameters(signature)
    ParameterValidator.validate_parsed_parameters(parameters)


@dataclass
class _Body:
    pass


def _error_body_parameter_kind_endpoint_handler(body: _Body, /) -> None:
    raise NotImplementedError


def _error_no_body_annotation_endpoint_handler(body) -> None:  # type: ignore[no-untyped-def]
    raise NotImplementedError


def _error_body_parameter_type_endpoint_handler(body: object) -> None:
    raise NotImplementedError


@pytest.mark.parametrize(
    "handler, match",
    [
        (
            _error_body_parameter_kind_endpoint_handler,
            "Invalid parameter kind for request body",
        ),
        (
            _error_no_body_annotation_endpoint_handler,
            "Missing annotation for request body",
        ),
        (
            _error_body_parameter_type_endpoint_handler,
            "Request body annotation must be a dataclass",
        ),
    ],
)
def test_invalid_body_parameter(handler: HandlerFunction, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        validate_endpoint_definition(EndpointDefinitionFactory.build(handler={"handler": handler}))


@dataclass
class _ModelA:
    type: Literal["a"]
    value: str


@dataclass
class _ModelB:
    type: Literal["b"]
    count: int


@dataclass
class _ModelWithDefault:
    value: str = "bad"


type _AliasedUnion = _ModelA | _ModelB
type _NestedAnnotatedAlias = Annotated[_AliasedUnion, "some_metadata"]
type _AliasedAnnotatedUnion = Annotated[_ModelA | _ModelB, Discriminator("type")]


def _handler_union_response() -> _ModelA | _ModelB:
    raise NotImplementedError


def _handler_aliased_union_response() -> _AliasedUnion:
    raise NotImplementedError


def _handler_nested_alias_response() -> _NestedAnnotatedAlias:
    raise NotImplementedError


def _handler_aliased_union_body(body: _AliasedUnion) -> _ModelA:
    raise NotImplementedError


def _handler_disc_alias_body(body: _AliasedAnnotatedUnion) -> _ModelA:
    raise NotImplementedError


def _handler_response_with_default() -> _ModelWithDefault:
    raise NotImplementedError


@pytest.mark.parametrize(
    "handler",
    [
        _handler_union_response,
        _handler_aliased_union_response,
        _handler_nested_alias_response,
    ],
)
def test_response_valid(handler: HandlerFunction) -> None:
    validate_endpoint_definition(
        EndpointDefinitionFactory.build(
            handler={"handler": handler},
            metadata={"content_type": "application/json"},
        )
    )


def test_response_with_default_invalid() -> None:
    with pytest.raises(ValueError, match="Forbidden `default`"):
        validate_endpoint_definition(
            EndpointDefinitionFactory.build(
                handler={"handler": _handler_response_with_default},
                metadata={"content_type": "application/json"},
            )
        )


@pytest.mark.parametrize(
    "handler",
    [
        _handler_aliased_union_body,
        _handler_disc_alias_body,
    ],
)
def test_request_body_valid(handler: HandlerFunction) -> None:
    validate_endpoint_definition(
        EndpointDefinitionFactory.build(
            handler={"handler": handler},
            metadata={"method": "post", "content_type": "application/json"},
        )
    )
