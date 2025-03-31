#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import enum
import http.client
from collections.abc import Iterator, Mapping, Sequence
from typing import Any, Callable

from apispec import APISpec
from werkzeug.utils import import_string

from livestatus import SiteId

from cmk.gui.config import active_config
from cmk.gui.openapi import endpoint_family_registry
from cmk.gui.openapi.restful_objects import Endpoint
from cmk.gui.openapi.restful_objects.api_error import (
    api_custom_error_schema,
    api_default_error_schema,
    ApiError,
)
from cmk.gui.openapi.restful_objects.parameters import (
    CONTENT_TYPE,
    ETAG_HEADER_PARAM,
    ETAG_IF_MATCH_HEADER,
    HEADER_CHECKMK_EDITION,
    HEADER_CHECKMK_VERSION,
)
from cmk.gui.openapi.restful_objects.params import marshmallow_to_openapi
from cmk.gui.openapi.restful_objects.type_defs import (
    ContentObject,
    ErrorStatusCodeInt,
    OpenAPIParameter,
    OpenAPITag,
    OperationObject,
    OperationSpecType,
    PathItem,
    RawParameter,
    ResponseType,
    StatusCodeInt,
)
from cmk.gui.openapi.spec.spec_generator._code_examples import code_samples
from cmk.gui.openapi.spec.spec_generator._documentation import (
    _add_once,
    _build_description,
    _coalesce_schemas,
    _docstring_description,
    _docstring_name,
    _permission_descriptions,
)
from cmk.gui.openapi.spec.spec_generator._type_defs import (
    MarshmallowSchemaDefinitions,
    SpecEndpoint,
)
from cmk.gui.permissions import permission_registry
from cmk.gui.utils import permission_verification as permissions


def _operation_dicts(spec: APISpec, endpoint: Endpoint) -> Iterator[tuple[str, OperationObject]]:
    """Generate the openapi spec part of this endpoint.

    The result needs to be added to the `apispec` instance manually.
    """
    deprecate_self: bool = False
    if endpoint.deprecated_urls is not None:
        for url, werk_id in endpoint.deprecated_urls.items():
            deprecate_self |= url == endpoint.path
            yield url, _marshmallow_endpoint_to_operation_dict(spec, endpoint, werk_id)

    if not deprecate_self:
        yield endpoint.path, _marshmallow_endpoint_to_operation_dict(spec, endpoint)


class DefaultStatusCodeDescription(enum.Enum):
    Code406 = "The requests accept headers can not be satisfied."
    Code401 = "The user is not authorized to do this request."
    Code403 = "Configuration via Setup is disabled."
    Code404 = "The requested object has not be found."
    Code422 = "The request could not be processed."
    Code423 = "The resource is currently locked."
    Code405 = "Method not allowed: This request is only allowed with other HTTP methods."
    Code409 = "The request is in conflict with the stored resource."
    Code415 = "The submitted content-type is not supported."
    Code302 = (
        "Either the resource has moved or has not yet completed. "
        "Please see this resource for further information."
    )
    Code400 = "Parameter or validation failure."
    Code412 = "The value of the If-Match header doesn't match the object's ETag."
    Code428 = "The required If-Match header is missing."
    Code200 = "The operation was done successfully."
    Code204 = "Operation done successfully. No further output."


DEFAULT_STATUS_CODE_SCHEMAS = {
    (406, DefaultStatusCodeDescription.Code406): api_default_error_schema(
        406,
        DefaultStatusCodeDescription.Code406.value,
    ),
    (401, DefaultStatusCodeDescription.Code401): api_default_error_schema(
        401,
        DefaultStatusCodeDescription.Code401.value,
    ),
    (403, DefaultStatusCodeDescription.Code403): api_default_error_schema(
        403,
        DefaultStatusCodeDescription.Code403.value,
    ),
    (404, DefaultStatusCodeDescription.Code404): api_default_error_schema(
        404,
        DefaultStatusCodeDescription.Code404.value,
    ),
    (422, DefaultStatusCodeDescription.Code422): api_default_error_schema(
        422,
        DefaultStatusCodeDescription.Code422.value,
    ),
    (423, DefaultStatusCodeDescription.Code423): api_default_error_schema(
        423,
        DefaultStatusCodeDescription.Code423.value,
    ),
    (405, DefaultStatusCodeDescription.Code405): api_default_error_schema(
        405,
        DefaultStatusCodeDescription.Code405.value,
    ),
    (409, DefaultStatusCodeDescription.Code409): api_default_error_schema(
        409,
        DefaultStatusCodeDescription.Code409.value,
    ),
    (415, DefaultStatusCodeDescription.Code415): api_default_error_schema(
        415,
        DefaultStatusCodeDescription.Code415.value,
    ),
    (400, DefaultStatusCodeDescription.Code400): api_default_error_schema(
        400,
        DefaultStatusCodeDescription.Code400.value,
    ),
    (412, DefaultStatusCodeDescription.Code412): api_default_error_schema(
        412,
        DefaultStatusCodeDescription.Code412.value,
    ),
    (428, DefaultStatusCodeDescription.Code428): api_default_error_schema(
        428,
        DefaultStatusCodeDescription.Code428.value,
    ),
}


def _marshmallow_endpoint_to_operation_dict(
    spec: APISpec, endpoint: Endpoint, werk_id: int | None = None
) -> OperationObject:
    assert endpoint.func is not None, "This object must be used in a decorator environment."
    assert endpoint.operation_id is not None, "This object must be used in a decorator environment."

    if (family_name := endpoint.family_name) is not None:
        family_tag_obj = _build_tag_obj_from_family(family_name)
    else:
        family_name, family_tag_obj = _build_tag_obj_from_module(
            import_string(endpoint.func.__module__)
        )
    _add_tag(spec, family_tag_obj, tag_group=endpoint.tag_group)

    schema_definitions = MarshmallowSchemaDefinitions(
        query_params=endpoint.query_params,
        path_params=endpoint.path_params,
        request_schema=endpoint.request_schema,
        response_schema=endpoint.response_schema,
        error_schemas=endpoint.error_schemas,
    )

    endpoint_title, endpoint_description = _endpoint_title_and_description_from_docstring(
        endpoint.func,
        endpoint.operation_id,
    )

    spec_endpoint = SpecEndpoint(
        title=endpoint_title,
        description=endpoint_description,
        path=endpoint.path,
        operation_id=endpoint.operation_id,
        family_name=family_name,
        etag=endpoint.etag,
        expected_status_codes=set(endpoint.expected_status_codes),
        content_type=endpoint.content_type,
        tag_group=endpoint.tag_group,
        method=endpoint.method,
        permissions_required=endpoint.permissions_required,
        permissions_description=endpoint.permissions_description,
        status_descriptions=endpoint.status_descriptions,
        does_redirects=endpoint.does_redirects,
    )
    return _to_operation_dict(spec, spec_endpoint, schema_definitions, werk_id)


def _endpoint_title_and_description_from_docstring(
    endpoint_func: Callable, operation_id: str
) -> tuple[str, str | None]:
    module_obj = import_string(endpoint_func.__module__)

    try:
        docstring_name = _docstring_name(endpoint_func.__doc__)
    except ValueError as exc:
        raise ValueError(
            f"Function {module_obj.__name__}:{endpoint_func.__name__} has no docstring."
        ) from exc

    if not docstring_name:
        raise RuntimeError(f"Please put a docstring onto {operation_id}")

    docstring_description = _docstring_description(endpoint_func.__doc__)
    return docstring_name, docstring_description


def _to_operation_dict(
    spec: APISpec,
    spec_endpoint: SpecEndpoint,
    schema_definitions: MarshmallowSchemaDefinitions,
    werk_id: int | None = None,
) -> OperationObject:
    assert spec_endpoint.operation_id is not None, (
        "This object must be used in a decorator environment."
    )

    response_headers: dict[str, OpenAPIParameter] = {}
    for header_to_add in [CONTENT_TYPE, HEADER_CHECKMK_EDITION, HEADER_CHECKMK_VERSION]:
        openapi_header = marshmallow_to_openapi([header_to_add], "header")[0]
        del openapi_header["in"]
        response_headers[openapi_header.pop("name")] = openapi_header

    if spec_endpoint.etag in ("output", "both"):
        etag_header = marshmallow_to_openapi([ETAG_HEADER_PARAM], "header")[0]
        del etag_header["in"]
        response_headers[etag_header.pop("name")] = etag_header

    responses: ResponseType = {}
    responses.update(
        MarshmallowResponses.generate_error_responses(
            spec_endpoint.expected_status_codes,
            spec_endpoint.status_descriptions,
            schema_definitions.error_schemas,
        )
    )
    responses.update(
        MarshmallowResponses.generate_success_responses(
            spec_endpoint.expected_status_codes,
            spec_endpoint.status_descriptions,
            spec_endpoint.content_type,
            schema_definitions.response_schema,
            response_headers,
        )
    )

    operation_spec: OperationSpecType = {
        "tags": [spec_endpoint.family_name],
        "description": _build_spec_description(
            endpoint_description=spec_endpoint.description,
            werk_id=werk_id,
            permissions_required=spec_endpoint.permissions_required,
            permissions_description=spec_endpoint.permissions_description,
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

    header_params: list[RawParameter] = []
    query_params: Sequence[RawParameter] = (
        schema_definitions.query_params if schema_definitions.query_params is not None else []
    )
    path_params: Sequence[RawParameter] = (
        schema_definitions.path_params if schema_definitions.path_params is not None else []
    )

    if active_config.rest_api_etag_locking and spec_endpoint.etag in ("input", "both"):
        header_params.append(ETAG_IF_MATCH_HEADER)

    if schema_definitions.request_schema:
        header_params.append(CONTENT_TYPE)

    # While we define the parameters separately to be able to use them for validation, the
    # OpenAPI spec expects them to be listed in on place, so here we bunch them together.
    operation_spec["parameters"] = _coalesce_schemas(
        [
            ("header", header_params),
            ("query", query_params),
            ("path", path_params),
        ]
    )

    operation_spec["responses"] = responses

    if schema_definitions.request_schema is not None:
        operation_spec["requestBody"] = {
            "required": True,
            "content": {
                "application/json": {
                    "schema": schema_definitions.request_schema,
                }
            },
        }

    operation_spec["x-codeSamples"] = code_samples(
        spec,
        spec_endpoint,
        schema_definitions,
        header_params=header_params,
        path_params=path_params,
        query_params=query_params,
    )

    # If we don't have any parameters we remove the empty list, so the spec will not have it.
    if not operation_spec["parameters"]:
        del operation_spec["parameters"]

    return {spec_endpoint.method: operation_spec}


def _build_spec_description(
    endpoint_description: str | None,
    werk_id: int | None,
    permissions_required: permissions.BasePerm | None,
    permissions_description: Mapping[str, str] | None,
) -> str:
    # The validator will complain on empty descriptions being set, even though it's valid.
    spec_description = _build_description(endpoint_description, werk_id)

    if permissions_required is not None:
        # Check that all the names are known to the system.
        for perm in permissions_required.iter_perms():
            if isinstance(perm, permissions.OkayToIgnorePerm):
                continue

            if perm.name not in permission_registry:
                # NOTE:
                #   See rest_api.py. dynamic_permission() have to be loaded before request
                #   for this to work reliably.
                raise RuntimeError(
                    f'Permission "{perm}" is not registered in the permission_registry.'
                )

        # Write permission documentation in openapi spec.
        if permissions_spec_description := _permission_descriptions(
            permissions_required, permissions_description
        ):
            if not spec_description:
                spec_description += "\n\n"
            spec_description += permissions_spec_description

    return spec_description


def _build_tag_obj_from_family(family_name: str) -> OpenAPITag:
    """Build a tag object from the endpoint family definition"""
    family = endpoint_family_registry.get(family_name)
    if family is None:
        raise ValueError(f"Family {family_name} not found in registry")

    return family.to_openapi_tag()


def _build_tag_obj_from_module(module_obj: Any) -> tuple[str, OpenAPITag]:
    """Build a tag object from the module's docstring"""
    docstring_name = _docstring_name(module_obj.__doc__)
    tag_obj: OpenAPITag = {
        "name": docstring_name,
        "x-displayName": docstring_name,
    }
    docstring_desc = _docstring_description(module_obj.__doc__)
    if docstring_desc:
        tag_obj["description"] = docstring_desc

    return docstring_name, tag_obj


class MarshmallowResponses:
    @staticmethod
    def generate_error_responses(
        expected_status_codes: set[StatusCodeInt],
        status_descriptions: Mapping[StatusCodeInt, str],
        error_schemas: Mapping[ErrorStatusCodeInt, type[ApiError]],
    ) -> ResponseType:
        """Generate the error responses dictionary for an operation"""
        responses: ResponseType = dict()

        # Always include 406
        responses["406"] = MarshmallowResponses._error_response_path_item(
            status_descriptions, error_schemas, 406, DefaultStatusCodeDescription.Code406
        )

        # 3xx responses
        if 302 in expected_status_codes:
            responses["302"] = MarshmallowResponses._path_item(
                status_descriptions, 302, DefaultStatusCodeDescription.Code302.value
            )

        if 303 in expected_status_codes:
            responses["303"] = MarshmallowResponses._path_item(
                status_descriptions, 303, DefaultStatusCodeDescription.Code302.value
            )

        # 4xx responses
        if 401 in expected_status_codes:
            responses["401"] = MarshmallowResponses._error_response_path_item(
                status_descriptions, error_schemas, 401, DefaultStatusCodeDescription.Code401
            )

        if 403 in expected_status_codes:
            responses["403"] = MarshmallowResponses._error_response_path_item(
                status_descriptions, error_schemas, 403, DefaultStatusCodeDescription.Code403
            )

        if 404 in expected_status_codes:
            responses["404"] = MarshmallowResponses._error_response_path_item(
                status_descriptions, error_schemas, 404, DefaultStatusCodeDescription.Code404
            )

        if 405 in expected_status_codes:
            responses["405"] = MarshmallowResponses._error_response_path_item(
                status_descriptions, error_schemas, 405, DefaultStatusCodeDescription.Code405
            )

        if 409 in expected_status_codes:
            responses["409"] = MarshmallowResponses._error_response_path_item(
                status_descriptions, error_schemas, 409, DefaultStatusCodeDescription.Code409
            )

        if 400 in expected_status_codes:
            responses["400"] = MarshmallowResponses._error_response_path_item(
                status_descriptions, error_schemas, 400, DefaultStatusCodeDescription.Code400
            )

        if 412 in expected_status_codes:
            responses["412"] = MarshmallowResponses._error_response_path_item(
                status_descriptions, error_schemas, 412, DefaultStatusCodeDescription.Code412
            )

        if 415 in expected_status_codes:
            responses["415"] = MarshmallowResponses._error_response_path_item(
                status_descriptions, error_schemas, 415, DefaultStatusCodeDescription.Code415
            )

        if 422 in expected_status_codes:
            responses["422"] = MarshmallowResponses._error_response_path_item(
                status_descriptions, error_schemas, 422, DefaultStatusCodeDescription.Code422
            )

        if 423 in expected_status_codes:
            responses["423"] = MarshmallowResponses._error_response_path_item(
                status_descriptions, error_schemas, 423, DefaultStatusCodeDescription.Code423
            )

        if 428 in expected_status_codes:
            responses["428"] = MarshmallowResponses._error_response_path_item(
                status_descriptions, error_schemas, 428, DefaultStatusCodeDescription.Code428
            )

        return responses

    @staticmethod
    def generate_success_responses(
        expected_status_codes: set[StatusCodeInt],
        status_descriptions: Mapping[StatusCodeInt, str] | None,
        content_type: str,
        response_schema: RawParameter | None,
        response_headers: dict[str, OpenAPIParameter],
    ) -> ResponseType:
        """Generate the success responses dictionary for an operation."""
        responses: ResponseType = {}

        # 2xx responses
        if 200 in expected_status_codes:
            if response_schema:
                content: ContentObject
                content = {content_type: {"schema": response_schema}}
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

            responses["200"] = MarshmallowResponses._path_item(
                status_descriptions,
                200,
                DefaultStatusCodeDescription.Code200.value,
                content=content,
                headers=response_headers,
            )

        if 204 in expected_status_codes:
            responses["204"] = MarshmallowResponses._path_item(
                status_descriptions, 204, DefaultStatusCodeDescription.Code204.value
            )

        return responses

    @staticmethod
    def _path_item(
        status_descriptions: Mapping[StatusCodeInt, str] | None,
        status_code: StatusCodeInt,
        description: str,
        content: dict[str, Any] | None = None,
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
        error_schemas: Mapping[ErrorStatusCodeInt, type[ApiError]],
        status_code: ErrorStatusCodeInt,
        default_description: DefaultStatusCodeDescription,
    ) -> PathItem:
        description = default_description.value
        schema = DEFAULT_STATUS_CODE_SCHEMAS.get((status_code, default_description))
        if status_code in status_descriptions:
            description = status_descriptions[status_code]
            schema = api_custom_error_schema(status_code, description)

        error_schema = error_schemas.get(status_code, schema)
        response: PathItem = {
            "description": f"{http.client.responses[status_code]}: {description}",
            "content": {"application/problem+json": {"schema": error_schema}},
        }
        return response


def _add_tag(spec: APISpec, tag: OpenAPITag, tag_group: str | None = None) -> None:
    name = tag["name"]
    if name in [t["name"] for t in spec._tags]:
        return

    spec.tag(dict(tag))
    if tag_group is not None:
        _assign_to_tag_group(spec, tag_group, name)


def _assign_to_tag_group(spec: APISpec, tag_group: str, name: str) -> None:
    for group in spec.options.setdefault("x-tagGroups", []):
        if group["name"] == tag_group:
            group["tags"].append(name)
            break
    else:
        raise ValueError(f"x-tagGroup {tag_group} not found. Please add it to specification.py")


def _add_cookie_auth(check_dict: dict[str, Any], site: SiteId) -> None:
    """Add the cookie authentication schema to the spec.

    We do this here, because every site has a different cookie name and such can't be predicted
    before this code here actually runs.
    """
    schema_name = "cookieAuth"
    _add_once(check_dict["security"], {schema_name: []})
    check_dict["components"]["securitySchemes"][schema_name] = {
        "in": "cookie",
        "name": f"auth_{site}",
        "type": "apiKey",
        "description": "Any user of Checkmk, who has already logged in, and thus got a cookie "
        "assigned, can use the REST API. Some actions may or may not succeed due "
        "to group and permission restrictions. This authentication method has the"
        "least precedence.",
    }
