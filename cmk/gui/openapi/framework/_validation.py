#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import dataclasses
import inspect
from collections.abc import Mapping
from typing import Annotated, cast, get_args, get_origin

from cmk.gui.openapi.restful_objects.type_defs import ErrorStatusCodeInt, StatusCodeInt
from cmk.gui.openapi.restful_objects.utils import identify_expected_status_codes
from cmk.gui.openapi.restful_objects.validators import PathParamsValidator

from .endpoint_model import EndpointModel, SignatureParametersProcessor
from .model import ApiOmitted
from .model.response import ApiErrorDataclass
from .registry import EndpointDefinition, RequestEndpoint
from .versioned_endpoint import HandlerFunction


def _validate_endpoint_parameters(handler: HandlerFunction) -> None:
    """Validate the parameters of the endpoint handler function"""
    signature = inspect.signature(handler, eval_str=True)
    annotated_parameters = SignatureParametersProcessor.extract_annotated_parameters(signature)
    SignatureParametersProcessor.validate_parameters(annotated_parameters)

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


def _type_contains_api_omitted(type_: type) -> bool:
    """Check if the type contains ApiOmitted"""
    if type_ is ApiOmitted:
        return True

    for arg in get_args(type_):
        if _type_contains_api_omitted(arg):
            return True

    return False


def _validate_defaults(
    operation_id: str,
    path: str,
    schema: type,
    other_defaults_allowed: bool,
) -> None:
    """Validate the model defaults"""
    if not dataclasses.is_dataclass(schema):
        raise ValueError(f"Endpoint {operation_id}: expected a dataclass annotation for `{path}`.")

    for field in dataclasses.fields(schema):
        if isinstance(field.type, str):
            raise ValueError(
                f"Endpoint {operation_id} uses a string annotation for `{path}.{field.name}`."
            )

        # without the cast we would have to check for GenericAlias, UnionType, DataclassInstance
        # and Literal. The dataclass instance check also has no proper return type
        type_ = cast(type, field.type)
        if dataclasses.is_dataclass(type_):
            _validate_defaults(
                operation_id, f"{path}.{field.name}", field.type, other_defaults_allowed
            )
            continue

        if _type_contains_api_omitted(type_):
            if field.default is not dataclasses.MISSING:
                raise ValueError(
                    f"Endpoint {operation_id} uses `default` for `{path}.{field.name}`. Use `default_factory=ApiOmitted` instead."
                )
            if field.default_factory is dataclasses.MISSING:
                raise ValueError(
                    f"Endpoint {operation_id} must set `default_factory=ApiOmitted` for `{path}.{field.name}`."
                )
            if field.default_factory is not ApiOmitted:
                raise ValueError(
                    f"Endpoint {operation_id} uses incorrect `default_factory` for `{path}.{field.name}`. Use `default=ApiOmitted` instead."
                )
            continue

        if other_defaults_allowed:
            continue

        if field.default is not dataclasses.MISSING:
            raise ValueError(
                f"Endpoint {operation_id} uses forbidden `default` for `{path}.{field.name}`."
            )
        if field.default_factory is not dataclasses.MISSING:
            raise ValueError(
                f"Endpoint {operation_id} uses forbidden `default_factory` for `{path}.{field.name}`."
            )


def _validate_endpoint_response_schema(endpoint: RequestEndpoint, model: EndpointModel) -> None:
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

    _validate_defaults(
        endpoint.operation_id, "response", model.response_body_type, other_defaults_allowed=False
    )


def _validate_endpoint_request_schema(endpoint: RequestEndpoint, model: EndpointModel) -> None:
    if model.request_body_type is None:
        return

    if endpoint.method in ("delete", "get"):
        # add an exception list if necessary but this should serve as double check that this is
        # intended
        raise ValueError(
            f"Endpoint {endpoint.operation_id} with method {endpoint.method} "
            f"should not have a request schema according to RFC"
        )

    _validate_defaults(
        endpoint.operation_id, "body", model.request_body_type, other_defaults_allowed=True
    )


def _validate_endpoint_error_schemas(
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


def _validate_endpoint_status_descriptions(
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


def validate_endpoint_definition(endpoint_definition: EndpointDefinition) -> None:
    """Validate a versioned endpoint configuration"""
    # TODO: this function should be invoked for custom endpoints
    endpoint = endpoint_definition.request_endpoint()
    try:
        _validate_endpoint_parameters(endpoint.handler)
    except ValueError as e:
        raise ValueError(f"Invalid handler for endpoint {endpoint.operation_id}: {e}") from None

    model = EndpointModel.build(endpoint.handler)
    _validate_endpoint_response_schema(endpoint, model)
    _validate_endpoint_request_schema(endpoint, model)
    _validate_endpoint_error_schemas(endpoint, endpoint_definition.handler.error_schemas)
    _validate_endpoint_status_descriptions(
        endpoint, model, endpoint_definition.handler.status_descriptions
    )
    PathParamsValidator.verify_path_params_presence(
        endpoint_definition.metadata.path, set(model.path_parameters)
    )
