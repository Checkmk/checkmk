#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import contextlib
import dataclasses
import inspect
import types
from collections.abc import Iterator, Mapping
from typing import Annotated, cast, get_args, get_origin

from cmk.gui.openapi.restful_objects.type_defs import ErrorStatusCodeInt, StatusCodeInt
from cmk.gui.openapi.restful_objects.utils import identify_expected_status_codes
from cmk.gui.openapi.restful_objects.validators import PathParamsValidator

from ._types import ApiContext, HeaderParam, PathParam, QueryParam
from ._utils import get_stripped_origin, strip_annotated
from .endpoint_model import EndpointModel, ParameterInfo, SignatureParametersProcessor
from .model import ApiOmitted
from .model.response import ApiErrorDataclass
from .registry import EndpointDefinition, RequestEndpoint
from .versioned_endpoint import HandlerFunction


@contextlib.contextmanager
def _with_endpoint_context(operation_id: str) -> Iterator[None]:
    try:
        yield
    except ValueError as e:
        raise ValueError(f"Endpoint {operation_id}: {e}") from None


def _type_contains_api_omitted(type_: type) -> bool:
    """Check if the type contains ApiOmitted"""
    if type_ is ApiOmitted:
        return True

    for arg in get_args(type_):
        if _type_contains_api_omitted(arg):
            return True

    return False


def _validate_defaults_parameter(
    path: str,
    field_type: type,
    field_default: object,
) -> None:
    """Validate the default values for parameters.

    If no default is set, `field_default` should be `dataclasses.MISSING`."""
    if dataclasses.is_dataclass(field_type):
        _validate_defaults_model(f"{path}", field_type, other_defaults_allowed=True)
        return

    if _type_contains_api_omitted(field_type):
        if field_default is dataclasses.MISSING:
            raise ValueError(f"Missing `ApiOmitted()` default value for `{path}`.")
        if not isinstance(field_default, ApiOmitted):
            raise ValueError(f"Invalid default value for `{path}`. Use `ApiOmitted()` instead.")
        return


def _validate_defaults_model(
    path: str,
    schema: type,
    *,
    other_defaults_allowed: bool,
) -> None:
    """Validate the model defaults.

    If `other_defaults_allowed` is true, `default` and `default_factory` are allowed to be set to
    any value, for types *not* containing `ApiOmitted`. This should be used only for request models.
    """
    if not dataclasses.is_dataclass(schema):
        raise ValueError(f"Expected a dataclass annotation for `{path}`.")

    for field in dataclasses.fields(schema):
        if isinstance(field.type, str):
            raise ValueError(f"String annotation for `{path}.{field.name}` is not allowed.")

        # without the cast we would have to check for GenericAlias, UnionType, DataclassInstance
        # and Literal. The dataclass instance check also has no proper return type
        type_ = cast(type, field.type)
        if dataclasses.is_dataclass(type_):
            _validate_defaults_model(
                f"{path}.{field.name}", field.type, other_defaults_allowed=other_defaults_allowed
            )
            continue

        if _type_contains_api_omitted(type_):
            if field.default is not dataclasses.MISSING:
                raise ValueError(
                    f"Invalid `default` for `{path}.{field.name}`. Use `default_factory=ApiOmitted` instead."
                )
            if field.default_factory is dataclasses.MISSING:
                raise ValueError(f"Missing `default_factory=ApiOmitted` for `{path}.{field.name}`.")
            if field.default_factory is not ApiOmitted:
                raise ValueError(
                    f"Invalid `default_factory` for `{path}.{field.name}`. Use `default=ApiOmitted` instead."
                )
            continue

        if other_defaults_allowed:
            continue

        if field.default is not dataclasses.MISSING:
            raise ValueError(f"Forbidden `default` for `{path}.{field.name}`.")
        if field.default_factory is not dataclasses.MISSING:
            raise ValueError(f"Forbidden `default_factory` for `{path}.{field.name}`.")


class ParameterValidator:
    @dataclasses.dataclass(slots=True)
    class Data:
        header_names: set[str] = dataclasses.field(default_factory=set)
        path_names: set[str] = dataclasses.field(default_factory=set)
        query_names: set[str] = dataclasses.field(default_factory=set)
        header_aliases: list[str] = dataclasses.field(default_factory=list)
        path_aliases: list[str] = dataclasses.field(default_factory=list)
        query_aliases: list[str] = dataclasses.field(default_factory=list)

    @staticmethod
    def validate_parsed_parameters(parsed_params: Mapping[str, ParameterInfo]) -> None:
        data = ParameterValidator.Data()

        for name, param_info in parsed_params.items():
            ParameterValidator._validate_kind_and_require_annotation(name, param_info)
            _validate_defaults_parameter(
                f"parameter.{name}", param_info.annotation, param_info.default
            )
            ParameterValidator._validate_source(data, name, param_info)

        ParameterValidator._validate_aliasing("query", data.query_names, data.query_aliases)
        ParameterValidator._validate_aliasing("path", data.path_names, data.path_aliases)
        ParameterValidator._validate_aliasing("header", data.header_names, data.header_aliases)

    @staticmethod
    def _validate_kind_and_require_annotation(name: str, param_info: ParameterInfo) -> None:
        if param_info.annotation is inspect.Parameter.empty:
            raise ValueError(f"Missing parameter annotation for parameter '{name}'")

        if param_info.kind not in (
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        ):
            raise ValueError(f"Invalid parameter kind for parameter '{name}'")

    @staticmethod
    def _validate_source(data: Data, name: str, param_info: ParameterInfo) -> None:
        if not param_info.sources:
            raise ValueError(f"Parameter '{name}' is missing a source annotation")

        if len(param_info.sources) > 1:
            raise ValueError(f"Multiple sources for parameter '{name}'")

        source = param_info.sources[0]

        if isinstance(source, HeaderParam):
            ParameterValidator._validate_header_param(data, name, source)

        elif isinstance(source, PathParam):
            ParameterValidator._validate_path_param(data, name, source)

        elif isinstance(source, QueryParam):
            ParameterValidator._validate_query_param(data, name, param_info, source)

    @staticmethod
    def _validate_header_param(data: Data, name: str, source: HeaderParam) -> None:
        # headers are case-insensitive, so we need to normalize the name and alias
        header_name = name.casefold()
        if header_name in data.header_names:
            raise ValueError(f"Duplicate header parameter (case-insensitive): {header_name}")
        data.header_names.add(header_name)

        if source.alias:
            data.header_aliases.append(source.alias.casefold())

    @staticmethod
    def _validate_path_param(data: Data, name: str, source: PathParam) -> None:
        data.path_names.add(name)

        if source.alias:
            data.path_aliases.append(source.alias)

    @staticmethod
    def _validate_query_param(
        data: Data, name: str, param_info: ParameterInfo, source: QueryParam
    ) -> None:
        data.query_names.add(name)

        if source.alias:
            data.query_aliases.append(source.alias)

        if source.is_list:
            origin = get_stripped_origin(param_info.annotation)
            if not issubclass(origin, list):
                if origin is types.UnionType:
                    if any(
                        issubclass(get_stripped_origin(arg), list)
                        for arg in get_args(strip_annotated(param_info.annotation))
                    ):
                        return
                raise ValueError(
                    f"Query parameter '{name}' is marked as list, but its type is not a list"
                )

    @staticmethod
    def _validate_aliasing(source: str, names: set[str], aliases: list[str]) -> None:
        aliases_set = set(aliases)
        if len(aliases_set) != len(aliases):
            duplicates = {name for name in aliases if aliases.count(name) > 1}
            raise ValueError(f"Duplicate alias in {source} parameters: {', '.join(duplicates)}")

        if duplicate := names & aliases_set:
            raise ValueError(f"Alias conflict in {source} parameters: {', '.join(duplicate)}")

        if "body" in aliases_set:
            raise ValueError("Cannot set alias to `body`")

        if "api_context" in aliases_set:
            raise ValueError("Cannot set alias to `api_context`")


class EndpointValidator:
    @staticmethod
    def _validate_parameters(handler: HandlerFunction) -> None:
        """Validate the parameters of the endpoint handler function"""
        signature = inspect.signature(handler, eval_str=True)
        annotated_parameters = SignatureParametersProcessor.extract_annotated_parameters(signature)
        ParameterValidator.validate_parsed_parameters(annotated_parameters)
        if "body" in signature.parameters:
            body = signature.parameters["body"]
            if body.kind not in (
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY,
            ):
                raise ValueError("Invalid parameter kind for request body")

            if body.annotation is inspect.Parameter.empty:
                raise ValueError("Missing annotation for request body")

            body_type = body.annotation
            while get_origin(body_type) is Annotated:
                body_type = get_args(body_type)[0]

            if not dataclasses.is_dataclass(body_type):
                raise ValueError("Request body annotation must be a dataclass")

        if "api_context" in signature.parameters:
            api_context = signature.parameters["api_context"]
            if api_context.kind not in (
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY,
            ):
                raise ValueError("Invalid parameter kind for api_context")

            if api_context.annotation is not ApiContext:
                raise ValueError("api_context must be annotated as `ApiContext`")

    @staticmethod
    def _validate_response_schema(endpoint: RequestEndpoint, model: EndpointModel) -> None:
        """Validate the response of the endpoint"""
        if model.response_body_type is None:
            if endpoint.content_type == "application/json":
                raise ValueError(
                    f"Endpoint {endpoint.operation_id} with content type {endpoint.content_type} "
                    f"requires a response schema."
                )
            return

        if endpoint.content_type != "application/json":
            raise ValueError(
                f"Endpoint {endpoint.operation_id} with content type {endpoint.content_type} "
                f"should not have a response schema."
            )

        with _with_endpoint_context(endpoint.operation_id):
            _validate_defaults_model(
                "response", model.response_body_type, other_defaults_allowed=False
            )

    @staticmethod
    def _validate_request_schema(endpoint: RequestEndpoint, model: EndpointModel) -> None:
        if model.request_body_type is None:
            return

        if endpoint.method in ("delete", "get"):
            # add an exception list if necessary but this should serve as double check that this is
            # intended
            raise ValueError(
                f"Endpoint {endpoint.operation_id} with method {endpoint.method} "
                f"should not have a request schema according to RFC"
            )

        with _with_endpoint_context(endpoint.operation_id):
            _validate_defaults_model("body", model.request_body_type, other_defaults_allowed=True)

    @staticmethod
    def _validate_error_schemas(
        endpoint: RequestEndpoint,
        error_schemas: Mapping[ErrorStatusCodeInt, type[ApiErrorDataclass]] | None,
    ) -> None:
        if not error_schemas:
            return

        for error_status_code in error_schemas:
            if error_status_code < 400:
                raise ValueError(
                    f"Endpoint {endpoint.operation_id} has error schema for status code "
                    f"{error_status_code} but this is not allowed."
                )

    @staticmethod
    def _validate_status_descriptions(
        endpoint: RequestEndpoint,
        model: EndpointModel,
        status_descriptions: Mapping[StatusCodeInt, str] | None,
    ) -> None:
        if not status_descriptions:
            return

        allowed_status_codes = identify_expected_status_codes(
            endpoint.method,
            endpoint.doc_group,
            endpoint.content_type,
            endpoint.etag,
            has_response=model.has_response_schema,
            has_path_params=model.has_path_parameters,
            has_query_params=model.has_query_parameters,
            has_request_schema=model.has_request_schema,
            additional_status_codes=endpoint.additional_status_codes,
        )

        for status_code in status_descriptions:
            if status_code not in allowed_status_codes:
                raise ValueError(
                    f"Endpoint {endpoint.operation_id} has custom status description for status code "
                    f"{status_code}, which is not used/declared."
                )

    @staticmethod
    def validate_endpoint_definition(endpoint_definition: EndpointDefinition) -> None:
        """Validate a versioned endpoint configuration"""
        # TODO: this function should be invoked for custom endpoints
        endpoint = endpoint_definition.request_endpoint()
        with _with_endpoint_context(endpoint.operation_id):
            EndpointValidator._validate_parameters(endpoint.handler)

        model = EndpointModel.build(endpoint.handler)
        EndpointValidator._validate_response_schema(endpoint, model)
        EndpointValidator._validate_request_schema(endpoint, model)
        EndpointValidator._validate_error_schemas(
            endpoint, endpoint_definition.handler.error_schemas
        )
        EndpointValidator._validate_status_descriptions(
            endpoint, model, endpoint_definition.handler.status_descriptions
        )
        PathParamsValidator.verify_path_params_presence(
            endpoint_definition.metadata.path, set(model.path_parameter_names.values())
        )
