#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

import dataclasses
import hashlib
import http.client
from collections.abc import Mapping, Sequence
from http import HTTPStatus
from typing import cast, Literal, TypeForm

from apispec import APISpec
from pydantic import PydanticInvalidForJsonSchema, TypeAdapter

from cmk.ccc.version import Edition
from cmk.gui.http import Response
from cmk.gui.openapi._type_adapter import get_cached_type_adapter
from cmk.gui.openapi.framework import APIVersion
from cmk.gui.openapi.framework._utils import get_dataclass_origin, iter_model_fields
from cmk.gui.openapi.framework.endpoint_model import EndpointModel
from cmk.gui.openapi.framework.model import api_field
from cmk.gui.openapi.framework.model.headers import (
    CONTENT_TYPE,
    ETAG_HEADER,
    ETAG_IF_MATCH_HEADER,
    HEADER_CHECKMK_EDITION,
    HEADER_CHECKMK_VERSION,
)
from cmk.gui.openapi.framework.model.response import ApiErrorDataclass
from cmk.gui.openapi.framework.registry import VersionedSpecEndpoint
from cmk.gui.openapi.restful_objects.type_defs import (
    ContentObject,
    ErrorStatusCodeInt,
    LocationType,
    OpenAPIParameter,
    OperationObject,
    OperationSpecType,
    PathItem,
    RedirectStatusCodeInt,
    ResponseType,
    StatusCodeInt,
    SuccessStatusCodeInt,
)
from cmk.gui.openapi.restful_objects.utils import (
    identify_expected_status_codes,
)
from cmk.gui.openapi.spec.plugin_pydantic import CheckmkGenerateJsonSchema
from cmk.gui.openapi.spec.spec_generator._code_examples import code_samples
from cmk.gui.openapi.spec.spec_generator._doc_utils import (
    add_tag,
    build_spec_description,
    build_tag_obj_from_family,
    endpoint_title_and_description_from_docstring,
    ERROR_DESCRIPTIONS,
    SUCCESS_DESCRIPTIONS,
)
from cmk.gui.openapi.spec.spec_generator._type_defs import DocEndpoint, SpecEndpoint
from cmk.gui.openapi.versioned_endpoint_map import EndpointVersionChange


def _is_response_subclass(value: object) -> bool:
    return isinstance(value, type) and issubclass(value, Response)


@dataclasses.dataclass(frozen=True, slots=True)
class PydanticSchemaDefinitions:
    model: EndpointModel
    error_schemas: Mapping[ErrorStatusCodeInt, type[ApiErrorDataclass]] | None = None

    def get_type(
        self, schema_type: Literal["body", "path", "query", "headers", "response"]
    ) -> TypeForm[object] | None:
        if schema_type == "response":
            return self.model.response_body_type

        return self.model.get_annotation(schema_type)

    def get_type_adapter(
        self, schema_type: Literal["body", "path", "query", "headers", "response"]
    ) -> TypeAdapter | None:
        if (type_ := self.get_type(schema_type)) is None:
            return None
        if _is_response_subclass(type_):
            return None
        # TypeAdapter performance: this is only used during spec generation
        return get_cached_type_adapter(type_)


def _extract_body_example(body_type: object) -> dict[str, object] | None:
    """Extract example values from a dataclass body type's field metadata.

    Returns a dict mapping each field's serialization alias (or name) to its
    example value, or None if body_type is None or no fields have examples.
    A parameterized generic model is walked with its type arguments substituted.
    """
    if body_type is None or get_dataclass_origin(body_type) is None:
        return None

    result: dict[str, object] = {}
    for field, field_type in iter_model_fields(body_type, path="body"):
        key = str(field.metadata.get("alias", field.name))
        if "examples" in field.metadata:
            result[key] = field.metadata["examples"][0]
        elif (nested := _extract_body_example(field_type)) is not None:
            result[key] = nested
    return result or None


def pydantic_endpoint_to_doc_endpoint(
    spec: APISpec,
    endpoint: VersionedSpecEndpoint,
    site_name: str,
    api_version: APIVersion,
    version_change: EndpointVersionChange | None = None,
) -> DocEndpoint:
    family_tag_obj = build_tag_obj_from_family(endpoint.family)
    add_tag(spec, family_tag_obj, tag_group=endpoint.doc_group)

    model = EndpointModel.build(endpoint.handler)

    schema_definitions = PydanticSchemaDefinitions(
        model=model,
        error_schemas=endpoint.error_schemas,
    )

    endpoint_title, endpoint_description = endpoint_title_and_description_from_docstring(
        endpoint.handler,
        endpoint.operation_id,
    )

    expected_status_codes = identify_expected_status_codes(
        endpoint.method,
        endpoint.doc_group,
        endpoint.content_type,
        endpoint.etag,
        has_response=model.has_response_schema,
        has_path_params=model.has_path_parameters,
        has_query_params=model.has_query_parameters,
        has_request_schema=model.has_request_schema,
        additional_status_codes=endpoint.additional_status_codes or [],
    )

    spec_endpoint = SpecEndpoint(
        title=endpoint_title,
        description=endpoint_description,
        path=endpoint.path,
        operation_id=endpoint.operation_id,
        family_name=endpoint.family,
        etag=endpoint.etag,
        expected_status_codes=expected_status_codes,
        content_type=endpoint.content_type,
        tag_group=endpoint.doc_group,
        method=endpoint.method,
        permissions_required=endpoint.permissions_required,
        permissions_description=endpoint.permissions_description,
        status_descriptions=endpoint.status_descriptions or {},
        does_redirects=bool(
            expected_status_codes
            & {
                HTTPStatus.CREATED,
                HTTPStatus.MOVED_PERMANENTLY,
                HTTPStatus.FOUND,
                HTTPStatus.SEE_OTHER,
            }
        ),
        supported_editions=endpoint.doc_supported_editions or set(Edition.__members__.values()),
        features_required=endpoint.doc_features_required,
    )
    try:
        return DocEndpoint(
            path=endpoint.path,
            effective_path=endpoint.path,
            method=endpoint.method,
            family_name=endpoint.family,
            doc_group=endpoint.doc_group,
            doc_sort_index=endpoint.doc_sort_index,
            operation_object=_to_operation_dict(
                spec,
                spec_endpoint,
                schema_definitions,
                site_name,
                api_version,
                endpoint.deprecated_werk_id,
                version_change,
            ),
        )
    except ValueError as e:
        raise ValueError(
            f"Failed to generate OpenAPI spec for endpoint {endpoint.operation_id}: {e}"
        ) from e


def _to_operation_dict(
    spec: APISpec,
    spec_endpoint: SpecEndpoint,
    schema_definitions: PydanticSchemaDefinitions,
    site_name: str,
    api_version: APIVersion,
    werk_id: int | None = None,
    version_change: EndpointVersionChange | None = None,
) -> OperationObject:
    response_headers: dict[str, OpenAPIParameter] = {}
    for header_to_add in [CONTENT_TYPE, HEADER_CHECKMK_EDITION, HEADER_CHECKMK_VERSION]:
        openapi_header = header_to_add.copy()
        del openapi_header["in"]
        response_headers[openapi_header.pop("name")] = openapi_header

    if spec_endpoint.etag in ("output", "both"):
        openapi_header = ETAG_HEADER.copy()
        del openapi_header["in"]
        response_headers[openapi_header.pop("name")] = openapi_header

    responses: ResponseType = {}
    responses.update(
        PydanticResponses.generate_error_responses(
            spec_endpoint.expected_status_codes,
            spec_endpoint.status_descriptions,
            schema_definitions.error_schemas or {},
        )
    )
    responses.update(
        PydanticResponses.generate_success_responses(
            spec_endpoint.expected_status_codes,
            spec_endpoint.status_descriptions,
            spec_endpoint.content_type,
            schema_definitions.get_type_adapter("response"),
            response_headers,
        )
    )

    operation_spec: OperationSpecType = {
        "tags": [spec_endpoint.family_name],
        "description": build_spec_description(
            endpoint_description=spec_endpoint.description,
            werk_id=werk_id,
            editions=spec_endpoint.supported_editions,
            permissions_required=spec_endpoint.permissions_required,
            permissions_description=spec_endpoint.permissions_description,
            version_change=version_change,
            features_required=spec_endpoint.features_required,
        ),
        "summary": spec_endpoint.title,
    }

    if werk_id:
        operation_spec["deprecated"] = True
        # ReDoc uses operationIds to build its URLs, so it needs a unique operationId,
        # otherwise links won't work properly.
        operation_spec["operationId"] = f"{spec_endpoint.operation_id}-{werk_id}"
    else:
        operation_spec["operationId"] = spec_endpoint.operation_id

    header_parameters: list[OpenAPIParameter] = []
    if spec_endpoint.etag in ("input", "both"):
        header_parameters.append(ETAG_IF_MATCH_HEADER)

    if schema_definitions.model.has_request_schema:
        header_parameters.append(CONTENT_TYPE)

    try:
        header_parameters.extend(_get_parameters("header", schema_definitions.get_type("headers")))
        path_parameters = _get_parameters("path", schema_definitions.get_type("path"))
        query_parameters = _get_parameters("query", schema_definitions.get_type("query"))
    except PydanticInvalidForJsonSchema as e:
        raise ValueError(f"Failed to generate parameter schemas: {e.message}") from e

    operation_spec["parameters"] = [*header_parameters, *path_parameters, *query_parameters]

    operation_spec["responses"] = responses

    if body_type_adapter := schema_definitions.get_type_adapter("body"):
        operation_spec["requestBody"] = {
            "required": True,
            "content": {
                "application/json": {
                    "schema": body_type_adapter,
                }
            },
        }

    operation_spec["x-codeSamples"] = code_samples(
        spec,
        spec_endpoint,
        request_schema_example=_extract_body_example(schema_definitions.get_type("body")),
        multiple_request_schemas=False,
        includes_redirect=False,
        header_params=header_parameters,
        path_params=path_parameters,
        query_params=query_parameters,
        site_name=site_name,
        api_version=api_version,
    )

    # If we don't have any parameters we remove the empty list, so the spec will not have it.
    if not operation_spec["parameters"]:
        del operation_spec["parameters"]

    return {spec_endpoint.method: operation_spec}


def _inline_refs(value: object, defs: dict[str, dict[str, object]]) -> None:
    """Inline all `$ref` references in the schema, so that `$defs` can be removed."""
    if isinstance(value, dict):
        while "$ref" in value:
            # loop, since some defs just reference other defs
            ref = str(value.pop("$ref")).removeprefix("#/$defs/")
            value.update(defs[ref])
        for _key, val in value.items():
            _inline_refs(val, defs)

    if isinstance(value, list):
        for item in value:
            _inline_refs(item, defs)


def _get_parameters(
    location: LocationType, schema: TypeForm[object] | None
) -> Sequence[OpenAPIParameter]:
    out: list[OpenAPIParameter] = []
    if schema is not None:
        # TypeAdapter: this is only used during spec generation
        json_schema = get_cached_type_adapter(schema).json_schema(
            by_alias=True,
            mode="validation",
            schema_generator=CheckmkGenerateJsonSchema,
            union_format="primitive_type_array",
        )

        if defs := json_schema.pop("$defs", None):
            # TODO: this is a workaround and should be cleaned up when we generate the spec manually
            _inline_refs(json_schema, defs)

        assert json_schema["type"] == "object", f"expected dataclass, got: {schema}"
        required_fields = set(json_schema.get("required", []))
        for name, field in json_schema["properties"].items():
            param: OpenAPIParameter = {
                "in": location,
                "name": name,
                "content": {"application/json": {"schema": field}},
            }
            if location == "path" or name in required_fields:
                param["required"] = True
            out.append(param)

    return out


class PydanticResponses:
    @staticmethod
    def generate_error_responses(
        expected_status_codes: set[StatusCodeInt],
        status_descriptions: Mapping[StatusCodeInt, str],
        error_schemas: Mapping[ErrorStatusCodeInt, type[ApiErrorDataclass]],
    ) -> ResponseType:
        """Generate the error responses dictionary for an operation"""
        responses: ResponseType = {}

        # Always include 406
        responses[HTTPStatus.NOT_ACCEPTABLE] = PydanticResponses._error_response_path_item(
            status_descriptions, error_schemas, HTTPStatus.NOT_ACCEPTABLE
        )

        # 3xx responses
        if HTTPStatus.FOUND in expected_status_codes:
            responses[HTTPStatus.FOUND] = PydanticResponses._path_item(
                status_descriptions, HTTPStatus.FOUND
            )

        if HTTPStatus.SEE_OTHER in expected_status_codes:
            responses[HTTPStatus.SEE_OTHER] = PydanticResponses._path_item(
                status_descriptions, HTTPStatus.SEE_OTHER
            )

        for status_code in ERROR_DESCRIPTIONS:
            if status_code in expected_status_codes:
                responses[status_code] = PydanticResponses._error_response_path_item(
                    status_descriptions, error_schemas, status_code
                )

        return responses

    @staticmethod
    def generate_success_responses(
        expected_status_codes: set[StatusCodeInt],
        status_descriptions: Mapping[StatusCodeInt, str] | None,
        content_type: str | None,
        response_type_adapter: TypeAdapter | None,
        response_headers: dict[str, OpenAPIParameter],
    ) -> ResponseType:
        """Generate the success responses dictionary for an operation."""
        responses: ResponseType = {}

        # 2xx responses
        if HTTPStatus.OK in expected_status_codes:
            if content_type is None:
                raise ValueError("Content-Type must be set for 200 responses.")
            if response_type_adapter:
                content: ContentObject = {content_type: {"schema": response_type_adapter}}
            elif content_type.startswith(("application/", "image/")):
                content = {
                    content_type: {
                        "schema": {
                            "type": "string",
                            "format": "binary",
                        }
                    }
                }
            else:
                raise ValueError(f"Unknown content-type: {content_type} Please add condition.")

            responses[HTTPStatus.OK] = PydanticResponses._path_item(
                status_descriptions,
                HTTPStatus.OK,
                content=content,
                headers=response_headers,
            )

        if HTTPStatus.NO_CONTENT in expected_status_codes:
            responses[HTTPStatus.NO_CONTENT] = PydanticResponses._path_item(
                status_descriptions, HTTPStatus.NO_CONTENT
            )

        return responses

    @staticmethod
    def _path_item(
        status_descriptions: Mapping[StatusCodeInt, str] | None,
        status_code: SuccessStatusCodeInt | RedirectStatusCodeInt,
        content: dict[str, dict[str, object]] | None = None,
        headers: dict[str, OpenAPIParameter] | None = None,
    ) -> PathItem:
        description = SUCCESS_DESCRIPTIONS[status_code]
        if status_descriptions and status_code in status_descriptions:
            description = status_descriptions[status_code]

        response: PathItem = {
            "description": f"{http.client.responses[status_code]}: {description}",
            "content": content if content is not None else {},
        }
        if headers:
            response["headers"] = headers
        return response

    @staticmethod
    def _error_response_path_item(
        status_descriptions: Mapping[StatusCodeInt, str],
        error_schemas: Mapping[ErrorStatusCodeInt, type[ApiErrorDataclass]],
        status_code: ErrorStatusCodeInt,
    ) -> PathItem:
        if status_code in status_descriptions:
            description = status_descriptions[status_code]
            schema = _api_error_schema("custom", status_code, description)
        else:
            description = ERROR_DESCRIPTIONS[status_code]
            schema = DEFAULT_STATUS_CODE_SCHEMAS[status_code]

        error_schema = error_schemas.get(status_code, schema)
        # TypeAdapter performance: this is only used during spec generation
        type_adapter = get_cached_type_adapter(error_schema)
        response: PathItem = {
            "description": f"{http.client.responses[status_code]}: {description}",
            "content": {"application/problem+json": {"schema": type_adapter}},
        }
        return response


def _api_error_schema(
    default_or_custom: Literal["default", "custom"],
    status_code: ErrorStatusCodeInt,
    description: str,
) -> type[ApiErrorDataclass]:
    # the type must have a unique name, so we need to include the description somehow
    desc_hash = hashlib.blake2b(description.encode(), digest_size=8).hexdigest().upper()
    return cast(
        type[ApiErrorDataclass],
        dataclasses.make_dataclass(
            f"Api{status_code}{default_or_custom.title()}Error{desc_hash}",
            fields=[
                (
                    "title",
                    str,
                    api_field(
                        description="A summary of the problem.",
                        example=http.client.responses[status_code],
                    ),
                ),
                (
                    "status",
                    int,
                    api_field(description="The HTTP status code.", example=int(status_code)),
                ),
                (
                    "detail",
                    str,
                    api_field(
                        description="Detailed information on what exactly went wrong.",
                        example=description,
                    ),
                ),
            ],
            bases=(ApiErrorDataclass,),
            kw_only=True,
            frozen=True,
        ),
    )


DEFAULT_STATUS_CODE_SCHEMAS = {
    status_code: _api_error_schema("default", status_code, description)
    for status_code, description in ERROR_DESCRIPTIONS.items()
}
