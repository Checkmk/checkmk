#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="comparison-overlap"

# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="no-untyped-call"

import hashlib
import http.client
from collections.abc import Iterator, Mapping, Sequence
from types import ModuleType

from apispec import APISpec
from apispec.ext.marshmallow import resolve_schema_instance  # type: ignore[attr-defined]
from marshmallow import Schema
from marshmallow.fields import Field
from marshmallow.schema import SchemaMeta
from werkzeug.utils import import_string

from cmk.ccc.version import Edition
from cmk.gui.openapi.framework.model.headers import (
    CONTENT_TYPE,
    ETAG_HEADER,
    ETAG_IF_MATCH_HEADER,
    HEADER_CHECKMK_EDITION,
    HEADER_CHECKMK_VERSION,
)
from cmk.gui.openapi.restful_objects import Endpoint
from cmk.gui.openapi.restful_objects.api_error import (
    api_custom_error_schema,
    api_default_error_schema,
    ApiError,
)
from cmk.gui.openapi.restful_objects.params import marshmallow_to_openapi
from cmk.gui.openapi.restful_objects.type_defs import (
    ContentObject,
    ErrorStatusCodeInt,
    LocationType,
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
from cmk.gui.openapi.spec.spec_generator._doc_utils import (
    _docstring_description,
    _docstring_name,
    add_tag,
    build_spec_description,
    build_tag_obj_from_family,
    DefaultStatusCodeDescription,
    endpoint_title_and_description_from_docstring,
)
from cmk.gui.openapi.spec.spec_generator._type_defs import (
    DocEndpoint,
    MarshmallowSchemaDefinitions,
    SpecEndpoint,
)


def marshmallow_doc_endpoints(
    spec: APISpec,
    endpoint: Endpoint,
    site_name: str,
) -> Iterator[DocEndpoint]:
    """Generate the openapi spec part of this endpoint.

    The result needs to be added to the `apispec` instance manually.
    """
    deprecate_self: bool = False
    if endpoint.deprecated_urls is not None:
        for url, werk_id in endpoint.deprecated_urls.items():
            deprecate_self |= url == endpoint.path
            yield _marshmallow_endpoint_to_doc_endpoint(url, spec, endpoint, site_name, werk_id)

    if not deprecate_self:
        yield _marshmallow_endpoint_to_doc_endpoint(endpoint.path, spec, endpoint, site_name)


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


def _marshmallow_endpoint_to_doc_endpoint(
    effective_path: str,
    spec: APISpec,
    endpoint: Endpoint,
    site_name: str,
    werk_id: int | None = None,
) -> DocEndpoint:
    assert endpoint.func is not None, "This object must be used in a decorator environment."
    assert endpoint.operation_id is not None, "This object must be used in a decorator environment."

    if (family_name := endpoint.family_name) is not None:
        family_tag_obj = build_tag_obj_from_family(family_name)
    else:
        family_name, family_tag_obj = _build_tag_obj_from_module(
            import_string(endpoint.func.__module__)
        )
    add_tag(spec, family_tag_obj, tag_group=endpoint.tag_group)

    schema_definitions = MarshmallowSchemaDefinitions(
        query_params=endpoint.query_params,
        path_params=endpoint.path_params,
        request_schema=endpoint.request_schema,
        response_schema=endpoint.response_schema,
        error_schemas=endpoint.error_schemas,
    )

    endpoint_title, endpoint_description = endpoint_title_and_description_from_docstring(
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
        supported_editions=endpoint.supported_editions or set(Edition.__members__.values()),
    )
    try:
        return DocEndpoint(
            path=endpoint.path,
            effective_path=effective_path,
            method=endpoint.method,
            family_name=family_name,
            doc_group=endpoint.tag_group,
            doc_sort_index=endpoint.sort,
            operation_object=_to_operation_dict(
                spec, spec_endpoint, schema_definitions, site_name, werk_id
            ),
        )
    except ValueError as e:
        raise ValueError(
            f"Failed to generate OpenAPI spec for endpoint {endpoint.operation_id}: {e}"
        ) from e


def _to_operation_dict(
    spec: APISpec,
    spec_endpoint: SpecEndpoint,
    schema_definitions: MarshmallowSchemaDefinitions,
    site_name: str,
    werk_id: int | None = None,
) -> OperationObject:
    response_headers: dict[str, OpenAPIParameter] = {}
    for header_to_add in [CONTENT_TYPE, HEADER_CHECKMK_EDITION, HEADER_CHECKMK_VERSION]:
        openapi_header = header_to_add.copy()
        del openapi_header["in"]
        response_headers[openapi_header.pop("name")] = openapi_header

    if spec_endpoint.etag in ("output", "both"):
        etag_header = ETAG_HEADER.copy()
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
        "description": build_spec_description(
            endpoint_description=spec_endpoint.description,
            werk_id=werk_id,
            editions=spec_endpoint.supported_editions,
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

    header_params: list[OpenAPIParameter] = []
    query_params: Sequence[RawParameter] = (
        schema_definitions.query_params if schema_definitions.query_params is not None else []
    )
    path_params: Sequence[RawParameter] = (
        schema_definitions.path_params if schema_definitions.path_params is not None else []
    )

    if spec_endpoint.etag in ("input", "both"):
        header_params.append(ETAG_IF_MATCH_HEADER)

    if schema_definitions.request_schema:
        header_params.append(CONTENT_TYPE)

    # While we define the parameters separately to be able to use them for validation, the
    # OpenAPI spec expects them to be listed in on place, so here we bunch them together.
    parameters = header_params.copy()
    parameters.extend(
        _coalesce_schemas(
            [
                ("query", query_params),
                ("path", path_params),
            ]
        )
    )
    operation_spec["parameters"] = parameters
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

    schema = _get_schema(schema_definitions.request_schema)
    if schema is not None:
        includes_redirect = "redirect" in schema.declared_fields
    else:
        includes_redirect = False
    operation_spec["x-codeSamples"] = code_samples(
        spec,
        spec_endpoint,
        request_schema_example=to_dict(schema) if schema else None,
        multiple_request_schemas=_schema_is_multiple(schema_definitions.request_schema),
        includes_redirect=includes_redirect,
        header_params=header_params,
        path_params=marshmallow_to_openapi(path_params, "path"),
        query_params=marshmallow_to_openapi(query_params, "query"),
        site_name=site_name,
    )

    # If we don't have any parameters we remove the empty list, so the spec will not have it.
    if not operation_spec["parameters"]:
        del operation_spec["parameters"]

    return {spec_endpoint.method: operation_spec}


def _build_tag_obj_from_module(module_obj: ModuleType) -> tuple[str, OpenAPITag]:
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
        content_type: str | None,
        response_schema: RawParameter | None,
        response_headers: dict[str, OpenAPIParameter],
    ) -> ResponseType:
        """Generate the success responses dictionary for an operation."""
        responses: ResponseType = {}

        # 2xx responses
        if 200 in expected_status_codes:
            if content_type is None:
                raise ValueError("Content-Type must be set for 200 responses.")
            if response_schema:
                content: ContentObject = {content_type: {"schema": response_schema}}
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


def _get_schema(
    schema: str | type[Schema] | None,
) -> Schema | None:
    """Get the schema instance of a schema name or class.

    In case of OneOfSchema classes, the first dispatched schema is being returned.

    Args:
        schema:
            Either

    Returns:
        A schema instance.

    """
    if schema is None:
        return None
    # NOTE:
    # In case of a "OneOfSchema" instance, we don't really have any fields on this Schema
    # as it is just there for dispatching. The real fields are on the dispatched classes.
    # We just take the first one and go with that, as we have no way of letting the user chose
    # the dispatching-key by himself (this is a limitation of ReDoc).
    _schema: Schema = resolve_schema_instance(schema)
    if _schema_is_multiple(schema):
        type_schemas = _schema.type_schemas  # type: ignore[attr-defined]
        first_key = list(type_schemas.keys())[0]
        _schema = resolve_schema_instance(type_schemas[first_key])

    if not hasattr(_schema, "schema_example"):
        raise ValueError(f"Schema {schema} does not have a schema_example attribute.")

    return _schema


def _schema_is_multiple(schema: str | type[Schema] | None) -> bool:
    if schema is None:
        return False
    _schema = resolve_schema_instance(schema)
    return bool(getattr(_schema, "type_schemas", None))


def to_dict(schema: Schema) -> dict[str, str]:
    """Convert a Schema-class to a dict-representation.

    Examples:

        >>> from cmk.gui.fields.utils import BaseSchema
        >>> from cmk import fields
        >>> class SayHello(BaseSchema):
        ...      message = fields.String(example="Hello world!")
        ...      message2 = fields.String(example="Hello Bob!")
        >>> to_dict(SayHello())
        {'message': 'Hello world!', 'message2': 'Hello Bob!'}

        >>> class Nobody(BaseSchema):
        ...      expects = fields.String()
        >>> to_dict(Nobody())
        Traceback (most recent call last):
        ...
        KeyError: "Field 'Nobody.expects' has no 'example'"

    Args:
        schema:
            A Schema instance with all it's fields having an `example` key.

    Returns:
        A dict with the field-names as a key and their example as value.

    """
    if (schema_example := getattr(schema, "schema_example", None)) is not None:
        return schema_example

    ret = {}
    for name, field in schema.declared_fields.items():
        try:
            ret[name] = field.metadata["example"]
        except KeyError as exc:
            raise KeyError(f"Field '{schema.__class__.__name__}.{name}' has no {exc}")
    return ret


def _coalesce_schemas(
    parameters: Sequence[tuple[LocationType, Sequence[RawParameter]]],
) -> Sequence[OpenAPIParameter]:
    rv: list[OpenAPIParameter] = []
    for location, params in parameters:
        if not params:
            continue

        to_convert: dict[str, Field] = {}
        for param in params:
            if isinstance(param, SchemaMeta):
                rv.append({"in": location, "schema": param})
            else:
                to_convert.update(param)

        if to_convert:
            rv.append({"in": location, "schema": _to_named_schema(to_convert)})

    return rv


def _to_named_schema(fields_: dict[str, Field]) -> type[Schema]:
    attrs: dict[str, Field | type] = dict(_patch_regex(fields_.copy()))
    attrs["Meta"] = type(
        "GeneratedMeta",
        (Schema.Meta,),
        {"register": True},
    )
    _hash = hashlib.sha256()

    def _update(d_: Mapping[str, Field]) -> None:
        for key, value in sorted(d_.items()):
            _hash.update(str(key).encode("utf-8"))
            if hasattr(value, "metadata"):
                _update(value.metadata)
            else:
                _hash.update(str(value).encode("utf-8"))

    _update(fields_)

    name = f"GeneratedSchema{_hash.hexdigest()}"
    schema_cls: type[Schema] = type(name, (Schema,), attrs)
    return schema_cls


def _patch_regex(fields: dict[str, Field]) -> dict[str, Field]:
    for _, value in fields.items():
        if "pattern" in value.metadata and value.metadata["pattern"].endswith(r"\Z"):
            value.metadata["pattern"] = value.metadata["pattern"][:-2] + "$"
    return fields
