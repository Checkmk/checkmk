#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import dataclasses
import http.client
from collections.abc import Mapping, Sequence
from typing import cast, Literal

from apispec import APISpec
from pydantic import PydanticInvalidForJsonSchema, TypeAdapter

from cmk.gui.openapi.framework.endpoint_model import EndpointModel
from cmk.gui.openapi.framework.model.api_field import api_field
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
    ResponseType,
    StatusCodeInt,
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
    DefaultStatusCodeDescription,
    endpoint_title_and_description_from_docstring,
    format_endpoint_supported_editions,
)
from cmk.gui.openapi.spec.spec_generator._type_defs import DocEndpoint, SpecEndpoint


@dataclasses.dataclass(frozen=True, slots=True)
class PydanticSchemaDefinitions:
    model: EndpointModel
    error_schemas: Mapping[ErrorStatusCodeInt, type[ApiErrorDataclass]] | None = None

    def get_type(
        self, schema_type: Literal["body", "path", "query", "headers", "response"]
    ) -> type | None:
        if schema_type == "response":
            return self.model.response_body_type

        return self.model.get_annotation(schema_type)

    def get_type_adapter(
        self, schema_type: Literal["body", "path", "query", "headers", "response"]
    ) -> TypeAdapter | None:
        if (type_ := self.get_type(schema_type)) is not None:
            # TypeAdapter performance: this is only used during spec generation
            return TypeAdapter(type_)  # nosemgrep: type-adapter-detected

        return None


def pydantic_endpoint_to_doc_endpoint(
    spec: APISpec, endpoint: VersionedSpecEndpoint, site_name: str
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
        does_redirects=bool(expected_status_codes & {201, 301, 302, 303}),
        supported_editions=endpoint.doc_supported_editions,
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
                spec, spec_endpoint, schema_definitions, site_name, endpoint.deprecated_werk_id
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
    werk_id: int | None = None,
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
            permissions_required=spec_endpoint.permissions_required,
            permissions_description=spec_endpoint.permissions_description,
        ),
        "summary": spec_endpoint.title,
    }

    if spec_endpoint.supported_editions:
        operation_spec["x-badges"] = format_endpoint_supported_editions(
            spec_endpoint.supported_editions
        )

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

    if schema_definitions.model.has_response_schema:
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
        request_schema_example=None,
        multiple_request_schemas=False,
        includes_redirect=False,
        header_params=header_parameters,
        path_params=path_parameters,
        query_params=query_parameters,
        site_name=site_name,
    )

    # If we don't have any parameters we remove the empty list, so the spec will not have it.
    if not operation_spec["parameters"]:
        del operation_spec["parameters"]

    return {spec_endpoint.method: operation_spec}


def _get_parameters(location: LocationType, schema: type | None) -> Sequence[OpenAPIParameter]:
    out: list[OpenAPIParameter] = []
    if schema is not None:
        # TypeAdapter: this is only used during spec generation
        json_schema = TypeAdapter(schema).json_schema(  # nosemgrep: type-adapter-detected
            by_alias=True, mode="validation", schema_generator=CheckmkGenerateJsonSchema
        )
        # TODO: inline $defs
        assert json_schema.get("$defs") is None, "$defs not yet supported in this context"
        assert json_schema["type"] == "object", f"expected dataclass, got: {schema.__name__}"
        for name, field in json_schema["properties"].items():
            param: OpenAPIParameter = {
                "in": location,
                "name": name,
                "content": {"application/json": {"schema": field}},
            }
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
        responses: ResponseType = dict()

        # Always include 406
        responses["406"] = PydanticResponses._error_response_path_item(
            status_descriptions, error_schemas, 406, DefaultStatusCodeDescription.Code406
        )

        # 3xx responses
        if 302 in expected_status_codes:
            responses["302"] = PydanticResponses._path_item(
                status_descriptions, 302, DefaultStatusCodeDescription.Code302.value
            )

        if 303 in expected_status_codes:
            responses["303"] = PydanticResponses._path_item(
                status_descriptions, 303, DefaultStatusCodeDescription.Code302.value
            )

        # 4xx responses
        if 401 in expected_status_codes:
            responses["401"] = PydanticResponses._error_response_path_item(
                status_descriptions, error_schemas, 401, DefaultStatusCodeDescription.Code401
            )

        if 403 in expected_status_codes:
            responses["403"] = PydanticResponses._error_response_path_item(
                status_descriptions, error_schemas, 403, DefaultStatusCodeDescription.Code403
            )

        if 404 in expected_status_codes:
            responses["404"] = PydanticResponses._error_response_path_item(
                status_descriptions, error_schemas, 404, DefaultStatusCodeDescription.Code404
            )

        if 405 in expected_status_codes:
            responses["405"] = PydanticResponses._error_response_path_item(
                status_descriptions, error_schemas, 405, DefaultStatusCodeDescription.Code405
            )

        if 409 in expected_status_codes:
            responses["409"] = PydanticResponses._error_response_path_item(
                status_descriptions, error_schemas, 409, DefaultStatusCodeDescription.Code409
            )

        if 400 in expected_status_codes:
            responses["400"] = PydanticResponses._error_response_path_item(
                status_descriptions, error_schemas, 400, DefaultStatusCodeDescription.Code400
            )

        if 412 in expected_status_codes:
            responses["412"] = PydanticResponses._error_response_path_item(
                status_descriptions, error_schemas, 412, DefaultStatusCodeDescription.Code412
            )

        if 415 in expected_status_codes:
            responses["415"] = PydanticResponses._error_response_path_item(
                status_descriptions, error_schemas, 415, DefaultStatusCodeDescription.Code415
            )

        if 422 in expected_status_codes:
            responses["422"] = PydanticResponses._error_response_path_item(
                status_descriptions, error_schemas, 422, DefaultStatusCodeDescription.Code422
            )

        if 423 in expected_status_codes:
            responses["423"] = PydanticResponses._error_response_path_item(
                status_descriptions, error_schemas, 423, DefaultStatusCodeDescription.Code423
            )

        if 428 in expected_status_codes:
            responses["428"] = PydanticResponses._error_response_path_item(
                status_descriptions, error_schemas, 428, DefaultStatusCodeDescription.Code428
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
        if 200 in expected_status_codes:
            if content_type is None:
                raise ValueError("Content-Type must be set for 200 responses.")
            if response_type_adapter:
                content: ContentObject = {content_type: {"schema": response_type_adapter}}
            elif content_type.startswith("application/") or content_type.startswith("image/"):
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

            responses["200"] = PydanticResponses._path_item(
                status_descriptions,
                200,
                DefaultStatusCodeDescription.Code200.value,
                content=content,
                headers=response_headers,
            )

        if 204 in expected_status_codes:
            responses["204"] = PydanticResponses._path_item(
                status_descriptions, 204, DefaultStatusCodeDescription.Code204.value
            )

        return responses

    @staticmethod
    def _path_item(
        status_descriptions: Mapping[StatusCodeInt, str] | None,
        status_code: StatusCodeInt,
        description: str,
        content: dict[str, dict[str, object]] | None = None,
        headers: dict[str, OpenAPIParameter] | None = None,
    ) -> PathItem:
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
        default_description: DefaultStatusCodeDescription,
    ) -> PathItem:
        description = default_description.value
        if status_code not in status_descriptions:
            schema = DEFAULT_STATUS_CODE_SCHEMAS.get((status_code, default_description))
        else:
            description = status_descriptions[status_code]
            schema = _api_error_schema("custom", status_code, description)

        error_schema = error_schemas.get(status_code, schema)
        # TypeAdapter performance: this is only used during spec generation
        type_adapter: TypeAdapter[ApiErrorDataclass]
        type_adapter = TypeAdapter(error_schema)  # nosemgrep: type-adapter-detected
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
    desc_hash = hash(description).to_bytes(length=8, signed=True).hex().upper()
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
                    api_field(description="The HTTP status code.", example=status_code),
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
        ),
    )


DEFAULT_STATUS_CODE_SCHEMAS = {
    (406, DefaultStatusCodeDescription.Code406): _api_error_schema(
        "default",
        406,
        DefaultStatusCodeDescription.Code406.value,
    ),
    (401, DefaultStatusCodeDescription.Code401): _api_error_schema(
        "default",
        401,
        DefaultStatusCodeDescription.Code401.value,
    ),
    (403, DefaultStatusCodeDescription.Code403): _api_error_schema(
        "default",
        403,
        DefaultStatusCodeDescription.Code403.value,
    ),
    (404, DefaultStatusCodeDescription.Code404): _api_error_schema(
        "default",
        404,
        DefaultStatusCodeDescription.Code404.value,
    ),
    (422, DefaultStatusCodeDescription.Code422): _api_error_schema(
        "default",
        422,
        DefaultStatusCodeDescription.Code422.value,
    ),
    (423, DefaultStatusCodeDescription.Code423): _api_error_schema(
        "default",
        423,
        DefaultStatusCodeDescription.Code423.value,
    ),
    (405, DefaultStatusCodeDescription.Code405): _api_error_schema(
        "default",
        405,
        DefaultStatusCodeDescription.Code405.value,
    ),
    (409, DefaultStatusCodeDescription.Code409): _api_error_schema(
        "default",
        409,
        DefaultStatusCodeDescription.Code409.value,
    ),
    (415, DefaultStatusCodeDescription.Code415): _api_error_schema(
        "default",
        415,
        DefaultStatusCodeDescription.Code415.value,
    ),
    (400, DefaultStatusCodeDescription.Code400): _api_error_schema(
        "default",
        400,
        DefaultStatusCodeDescription.Code400.value,
    ),
    (412, DefaultStatusCodeDescription.Code412): _api_error_schema(
        "default",
        412,
        DefaultStatusCodeDescription.Code412.value,
    ),
    (428, DefaultStatusCodeDescription.Code428): _api_error_schema(
        "default",
        428,
        DefaultStatusCodeDescription.Code428.value,
    ),
}
