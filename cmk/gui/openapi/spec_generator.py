#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import enum
import hashlib
import http.client
from collections.abc import Iterator, Sequence
from typing import Any, get_args

import openapi_spec_validator
from apispec import APISpec
from apispec.utils import dedent
from marshmallow import Schema
from marshmallow.schema import SchemaMeta
from werkzeug.utils import import_string

from livestatus import SiteId

import cmk.utils.version as cmk_version
from cmk.utils import store
from cmk.utils.site import omd_site

from cmk.gui import main_modules
from cmk.gui.config import active_config
from cmk.gui.fields import Field
from cmk.gui.openapi.restful_objects import permissions
from cmk.gui.openapi.restful_objects.api_error import (
    api_custom_error_schema,
    api_default_error_schema,
)
from cmk.gui.openapi.restful_objects.code_examples import code_samples
from cmk.gui.openapi.restful_objects.decorators import Endpoint
from cmk.gui.openapi.restful_objects.parameters import (
    CONTENT_TYPE,
    ETAG_HEADER_PARAM,
    ETAG_IF_MATCH_HEADER,
    HEADER_CHECKMK_EDITION,
    HEADER_CHECKMK_VERSION,
)
from cmk.gui.openapi.restful_objects.params import to_openapi
from cmk.gui.openapi.restful_objects.registry import endpoint_registry
from cmk.gui.openapi.restful_objects.specification import make_spec, spec_path
from cmk.gui.openapi.restful_objects.type_defs import (
    ContentObject,
    EndpointTarget,
    ErrorStatusCodeInt,
    LocationType,
    OpenAPIParameter,
    OpenAPITag,
    OperationObject,
    OperationSpecType,
    PathItem,
    RawParameter,
    ResponseType,
    SchemaParameter,
    StatusCodeInt,
)
from cmk.gui.permissions import permission_registry
from cmk.gui.session import SuperUserContext
from cmk.gui.utils import get_failed_plugins
from cmk.gui.utils.script_helpers import gui_context

Ident = tuple[str, str]


def main() -> int:
    main_modules.load_plugins()
    if errors := get_failed_plugins():
        raise Exception(f"The following errors occured during plug-in loading: {errors}")

    with gui_context(), SuperUserContext():
        for target in get_args(EndpointTarget):
            store.save_object_to_file(
                spec_path(target),
                _generate_spec(make_spec(), target, omd_site()),
                pretty=False,
            )
    return 0


def _generate_spec(
    spec: APISpec, target: EndpointTarget, site: SiteId, validate: bool = True
) -> dict[str, Any]:
    endpoint: Endpoint

    methods = ["get", "put", "post", "delete"]

    undocumented_tag_groups = ["Undocumented Endpoint"]

    if cmk_version.edition() is cmk_version.Edition.CRE:
        undocumented_tag_groups.append("Checkmk Internal")

    def module_name(func: Any) -> str:
        return f"{func.__module__}.{func.__name__}"

    def sort_key(e: Endpoint) -> tuple[str | int, ...]:
        return e.sort, module_name(e.func), methods.index(e.method), e.path

    seen_paths: dict[Ident, OperationObject] = {}
    ident: Ident
    for endpoint in sorted(endpoint_registry, key=sort_key):
        if target in endpoint.blacklist_in or endpoint.tag_group in undocumented_tag_groups:
            continue

        for path, operation_dict in _operation_dicts(spec, endpoint):
            ident = endpoint.method, path
            if ident in seen_paths:
                raise ValueError(
                    f"{ident} has already been defined.\n\n"
                    f"This one: {operation_dict}\n\n"
                    f"The previous one: {seen_paths[ident]}\n\n"
                )
            seen_paths[ident] = operation_dict
            spec.path(path=path, operations={str(k): v for k, v in operation_dict.items()})

    del seen_paths

    generated_spec = spec.to_dict()
    _add_cookie_auth(generated_spec, site)
    if not validate:
        return generated_spec

    # TODO: Need to investigate later what is going on here after cleaning up a bit further
    openapi_spec_validator.validate(generated_spec)  # type: ignore[arg-type]
    return generated_spec


def _operation_dicts(spec: APISpec, endpoint: Endpoint) -> Iterator[tuple[str, OperationObject]]:
    """Generate the openapi spec part of this endpoint.

    The result needs to be added to the `apispec` instance manually.
    """
    deprecate_self: bool = False
    if endpoint.deprecated_urls is not None:
        for url, werk_id in endpoint.deprecated_urls.items():
            deprecate_self |= url == endpoint.path
            yield url, _to_operation_dict(spec, endpoint, werk_id)

    if not deprecate_self:
        yield endpoint.path, _to_operation_dict(spec, endpoint)


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


def _to_operation_dict(  # pylint: disable=too-many-branches
    spec: APISpec,
    endpoint: Endpoint,
    werk_id: int | None = None,
) -> OperationObject:
    assert endpoint.func is not None, "This object must be used in a decorator environment."
    assert endpoint.operation_id is not None, "This object must be used in a decorator environment."

    module_obj = import_string(endpoint.func.__module__)

    response_headers: dict[str, OpenAPIParameter] = {}
    for header_to_add in [CONTENT_TYPE, HEADER_CHECKMK_EDITION, HEADER_CHECKMK_VERSION]:
        openapi_header = to_openapi([header_to_add], "header")[0]
        del openapi_header["in"]
        response_headers[openapi_header.pop("name")] = openapi_header

    if endpoint.etag in ("output", "both"):
        etag_header = to_openapi([ETAG_HEADER_PARAM], "header")[0]
        del etag_header["in"]
        response_headers[etag_header.pop("name")] = etag_header

    responses: ResponseType = {}

    responses["406"] = _error_response_path_item(
        endpoint, 406, DefaultStatusCodeDescription.Code406
    )

    if 401 in endpoint.expected_status_codes:
        responses["401"] = _error_response_path_item(
            endpoint, 401, DefaultStatusCodeDescription.Code401
        )

    if 403 in endpoint.expected_status_codes:
        responses["403"] = _error_response_path_item(
            endpoint, 403, DefaultStatusCodeDescription.Code403
        )

    if 404 in endpoint.expected_status_codes:
        responses["404"] = _error_response_path_item(
            endpoint, 404, DefaultStatusCodeDescription.Code404
        )

    if 422 in endpoint.expected_status_codes:
        responses["422"] = _error_response_path_item(
            endpoint, 422, DefaultStatusCodeDescription.Code422
        )

    if 423 in endpoint.expected_status_codes:
        responses["423"] = _error_response_path_item(
            endpoint, 423, DefaultStatusCodeDescription.Code423
        )

    if 405 in endpoint.expected_status_codes:
        responses["405"] = _error_response_path_item(
            endpoint, 405, DefaultStatusCodeDescription.Code405
        )

    if 409 in endpoint.expected_status_codes:
        responses["409"] = _error_response_path_item(
            endpoint, 409, DefaultStatusCodeDescription.Code409
        )

    if 415 in endpoint.expected_status_codes:
        responses["415"] = _error_response_path_item(
            endpoint, 415, DefaultStatusCodeDescription.Code415
        )

    if 302 in endpoint.expected_status_codes:
        responses["302"] = _path_item(endpoint, 302, DefaultStatusCodeDescription.Code302.value)

    if 400 in endpoint.expected_status_codes:
        responses["400"] = _error_response_path_item(
            endpoint, 400, DefaultStatusCodeDescription.Code400
        )

    # We don't(!) support any endpoint without an output schema.
    # Just define one!
    if 200 in endpoint.expected_status_codes:
        if endpoint.response_schema:
            content: ContentObject
            content = {endpoint.content_type: {"schema": endpoint.response_schema}}
        elif endpoint.content_type.startswith("application/") or endpoint.content_type.startswith(
            "image/"
        ):
            content = {
                endpoint.content_type: {
                    "schema": {
                        "type": "string",
                        "format": "binary",
                    }
                }
            }
        else:
            raise ValueError(f"Unknown content-type: {endpoint.content_type} Please add condition.")
        responses["200"] = _path_item(
            endpoint,
            200,
            DefaultStatusCodeDescription.Code200.value,
            content=content,
            headers=response_headers,
        )

    if 204 in endpoint.expected_status_codes:
        responses["204"] = _path_item(endpoint, 204, DefaultStatusCodeDescription.Code204.value)

    if 412 in endpoint.expected_status_codes:
        responses["412"] = _error_response_path_item(
            endpoint, 412, DefaultStatusCodeDescription.Code412
        )

    if 428 in endpoint.expected_status_codes:
        responses["428"] = _error_response_path_item(
            endpoint, 428, DefaultStatusCodeDescription.Code428
        )

    docstring_name = _docstring_name(module_obj.__doc__)
    tag_obj: OpenAPITag = {
        "name": docstring_name,
        "x-displayName": docstring_name,
    }
    docstring_desc = _docstring_description(module_obj.__doc__)
    if docstring_desc:
        tag_obj["description"] = docstring_desc

    _add_tag(spec, tag_obj, tag_group=endpoint.tag_group)

    operation_spec: OperationSpecType = {
        "tags": [docstring_name],
        "description": "",
    }
    if werk_id:
        operation_spec["deprecated"] = True
        # ReDoc uses operationIds to build its URLs, so it needs a unique operationId,
        # otherwise links won't work properly.
        operation_spec["operationId"] = f"{endpoint.operation_id}-{werk_id}"
    else:
        operation_spec["operationId"] = endpoint.operation_id

    header_params: list[RawParameter] = []
    query_params: Sequence[RawParameter] = (
        endpoint.query_params if endpoint.query_params is not None else []
    )
    path_params: Sequence[RawParameter] = (
        endpoint.path_params if endpoint.path_params is not None else []
    )

    if active_config.rest_api_etag_locking and endpoint.etag in ("input", "both"):
        header_params.append(ETAG_IF_MATCH_HEADER)

    if endpoint.request_schema:
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

    if endpoint.request_schema is not None:
        operation_spec["requestBody"] = {
            "required": True,
            "content": {
                "application/json": {
                    "schema": endpoint.request_schema,
                }
            },
        }

    operation_spec["x-codeSamples"] = code_samples(
        spec,
        endpoint,
        header_params=header_params,
        path_params=path_params,
        query_params=query_params,
    )

    # If we don't have any parameters we remove the empty list, so the spec will not have it.
    if not operation_spec["parameters"]:
        del operation_spec["parameters"]

    try:
        docstring_name = _docstring_name(endpoint.func.__doc__)
    except ValueError as exc:
        raise ValueError(
            f"Function {module_obj.__name__}:{endpoint.func.__name__} has no docstring."
        ) from exc

    if docstring_name:
        operation_spec["summary"] = docstring_name
    else:
        raise RuntimeError(f"Please put a docstring onto {endpoint.operation_id}")

    if description := _build_description(_docstring_description(endpoint.func.__doc__), werk_id):
        # The validator will complain on empty descriptions being set, even though it's valid.
        operation_spec["description"] = description

    if endpoint.permissions_required is not None:
        # Check that all the names are known to the system.
        for perm in endpoint.permissions_required.iter_perms():
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
        if description := _permission_descriptions(
            endpoint.permissions_required, endpoint.permissions_description
        ):
            operation_spec.setdefault("description", "")
            if not operation_spec["description"]:
                operation_spec["description"] += "\n\n"
            operation_spec["description"] += description

    return {endpoint.method: operation_spec}


def _build_description(description_text: str | None, werk_id: int | None = None) -> str:
    r"""Build a OperationSpecType description.

    Examples:

        >>> _build_description(None)
        ''

        >>> _build_description("Foo")
        'Foo'

        >>> _build_description(None, 12345)
        '`WARNING`: This URL is deprecated, see [Werk 12345](https://checkmk.com/werk/12345) for more details.\n\n'

        >>> _build_description('Foo', 12345)
        '`WARNING`: This URL is deprecated, see [Werk 12345](https://checkmk.com/werk/12345) for more details.\n\nFoo'

    Args:
        description_text:
            The text of the description. This may be None.

        werk_id:
            A Werk ID for a deprecation warning. This may be None.

    Returns:
        Either a complete description or None

    """
    if werk_id:
        werk_link = f"https://checkmk.com/werk/{werk_id}"
        description = (
            f"`WARNING`: This URL is deprecated, see [Werk {werk_id}]({werk_link}) for more "
            "details.\n\n"
        )
    else:
        description = ""

    if description_text is not None:
        description += description_text

    return description


def _schema_name(schema_name: str):  # type: ignore[no-untyped-def]
    """Remove the suffix 'Schema' from a schema-name.

    Examples:

        >>> _schema_name("BakeSchema")
        'Bake'

        >>> _schema_name("BakeSchemaa")
        'BakeSchemaa'

    Args:
        schema_name:
            The name of the Schema.

    Returns:
        The name of the Schema, maybe stripped of the suffix 'Schema'.

    """
    return schema_name[:-6] if schema_name.endswith("Schema") else schema_name


def _schema_definition(schema_name: str):  # type: ignore[no-untyped-def]
    ref = f"#/components/schemas/{_schema_name(schema_name)}"
    return f'<SchemaDefinition schemaRef="{ref}" showReadOnly={{true}} showWriteOnly={{true}} />'


def _permission_descriptions(
    perms: permissions.BasePerm,
    descriptions: dict[str, str] | None = None,
) -> str:
    r"""Describe permissions human-readable

    Args:
        perms:
        descriptions:

    Examples:

        >>> _permission_descriptions(
        ...     permissions.Perm("wato.edit_folders"),
        ...     {'wato.edit_folders': 'Allowed to cook the books.'},
        ... )
        'This endpoint requires the following permissions: \n * `wato.edit_folders`: Allowed to cook the books.\n'

        >>> _permission_descriptions(
        ...     permissions.AllPerm([permissions.Perm("wato.edit_folders")]),
        ...     {'wato.edit_folders': 'Allowed to cook the books.'},
        ... )
        'This endpoint requires the following permissions: \n * `wato.edit_folders`: Allowed to cook the books.\n'

        >>> _permission_descriptions(
        ...     permissions.AllPerm([permissions.Perm("wato.edit_folders"),
        ...                          permissions.Undocumented(permissions.Perm("wato.edit"))]),
        ...     {'wato.edit_folders': 'Allowed to cook the books.'},
        ... )
        'This endpoint requires the following permissions: \n * `wato.edit_folders`: Allowed to cook the books.\n'

        >>> _permission_descriptions(
        ...     permissions.AnyPerm([permissions.Perm("wato.edit_folders"), permissions.Perm("wato.edit_folders")]),
        ...     {'wato.edit_folders': 'Allowed to cook the books.'},
        ... )
        'This endpoint requires the following permissions: \n * Any of:\n   * `wato.edit_folders`: Allowed to cook the books.\n   * `wato.edit_folders`: Allowed to cook the books.\n'

        The description will have a structure like this:

            * Any of:
               * c
               * All of:
                  * a
                  * b

        >>> _permission_descriptions(
        ...     permissions.AnyPerm([
        ...         permissions.Perm("c"),
        ...         permissions.AllPerm([
        ...              permissions.Perm("a"),
        ...              permissions.Perm("b"),
        ...         ]),
        ...     ]),
        ...     {'a': 'Hold a', 'b': 'Hold b', 'c': 'Hold c'}
        ... )
        'This endpoint requires the following permissions: \n * Any of:\n   * `c`: Hold c\n   * All of:\n     * `a`: Hold a\n     * `b`: Hold b\n'

    Returns:
        The description as a string.

    """
    description_map: dict[str, str] = descriptions if descriptions is not None else {}
    _description: list[str] = ["This endpoint requires the following permissions: "]

    def _count_perms(_perms):
        return len([p for p in _perms if not isinstance(p, permissions.Undocumented)])

    def _add_desc(  # pylint: disable=too-many-branches
        permission: permissions.BasePerm, indent: int, desc_list: list[str]
    ) -> None:
        if isinstance(permission, permissions.Undocumented):
            # Don't render
            return

        # We indent by two spaces, as is required by markdown.
        prefix = "  " * indent
        if isinstance(permission, (permissions.Perm, permissions.OkayToIgnorePerm)):
            perm_name = permission.name
            try:
                desc = description_map.get(perm_name) or permission_registry[perm_name].description
            except KeyError:
                if isinstance(permission, permissions.OkayToIgnorePerm):
                    return
                raise
            _description.append(f"{prefix} * `{perm_name}`: {desc}")
        elif isinstance(permission, permissions.AllPerm):
            # If AllOf only contains one permission, we don't need to show the AllOf
            if _count_perms(permission.perms) == 1:
                _add_desc(permission.perms[0], indent, desc_list)
            else:
                desc_list.append(f"{prefix} * All of:")
                for perm in permission.perms:
                    _add_desc(perm, indent + 1, desc_list)
        elif isinstance(permission, permissions.AnyPerm):
            # If AnyOf only contains one permission, we don't need to show the AnyOf
            if _count_perms(permission.perms) == 1:
                _add_desc(permission.perms[0], indent, desc_list)
            else:
                desc_list.append(f"{prefix} * Any of:")
                for perm in permission.perms:
                    _add_desc(perm, indent + 1, desc_list)
        elif isinstance(permission, permissions.Optional):
            desc_list.append(f"{prefix} * Optionally:")
            _add_desc(permission.perm, indent + 1, desc_list)
        else:
            raise NotImplementedError(f"Printing of {permission!r} not yet implemented.")

    _add_desc(perms, 0, _description)
    return "\n".join(_description) + "\n"


def _path_item(
    endpoint: Endpoint,
    status_code: StatusCodeInt,
    description: str,
    content: dict[str, Any] | None = None,
    headers: dict[str, OpenAPIParameter] | None = None,
) -> PathItem:
    if status_code in endpoint.status_descriptions:
        description = endpoint.status_descriptions[status_code]

    response: PathItem = {
        "description": f"{http.client.responses[status_code]}: {description}",
        "content": content if content is not None else {},
    }
    if headers:
        response["headers"] = headers
    return response


def _error_response_path_item(
    endpoint: Endpoint,
    status_code: ErrorStatusCodeInt,
    default_description: DefaultStatusCodeDescription,
) -> PathItem:
    description = default_description.value
    schema = DEFAULT_STATUS_CODE_SCHEMAS.get((status_code, default_description))
    if status_code in endpoint.status_descriptions:
        description = endpoint.status_descriptions[status_code]
        schema = api_custom_error_schema(status_code, description)

    error_schema = endpoint.error_schemas.get(status_code, schema)
    response: PathItem = {
        "description": f"{http.client.responses[status_code]}: {description}",
        "content": {"application/problem+json": {"schema": error_schema}},
    }
    return response


def _coalesce_schemas(
    parameters: Sequence[tuple[LocationType, Sequence[RawParameter]]],
) -> Sequence[SchemaParameter]:
    rv: list[SchemaParameter] = []
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


def _patch_regex(fields: dict[str, Field]) -> dict[str, Field]:
    for _, value in fields.items():
        if "pattern" in value.metadata and value.metadata["pattern"].endswith(r"\Z"):
            value.metadata["pattern"] = value.metadata["pattern"][:-2] + "$"
    return fields


def _to_named_schema(fields_: dict[str, Field]) -> type[Schema]:
    attrs: dict[str, Any] = _patch_regex(fields_.copy())
    attrs["Meta"] = type(
        "GeneratedMeta",
        (Schema.Meta,),
        {"register": True, "ordered": True},
    )
    _hash = hashlib.sha256()

    def _update(d_):
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


def _docstring_description(docstring: str | None) -> str | None:
    """Split the docstring by title and rest.

    This is part of the rest.

    >>> _docstring_description(_docstring_description.__doc__).split("\\n")[0]
    'This is part of the rest.'

    Args:
        docstring:

    Returns:
        A string or nothing.

    """
    if not docstring:
        return None
    parts = dedent(docstring).split("\n\n", 1)
    if len(parts) > 1:
        return parts[1].strip()
    return None


def _docstring_name(docstring: str | None) -> str:
    """Split the docstring by title and rest.

    This is part of the rest.

    >>> _docstring_name(_docstring_name.__doc__)
    'Split the docstring by title and rest.'

    >>> _docstring_name("")
    Traceback (most recent call last):
    ...
    ValueError: No name for the module defined. Please add a docstring!

    Args:
        docstring:

    Returns:
        A string or nothing.

    """ ""
    if not docstring:
        raise ValueError("No name for the module defined. Please add a docstring!")

    return [part.strip() for part in dedent(docstring).split("\n\n", 1)][0]


def _add_once(coll: list[dict[str, Any]], to_add: dict[str, Any]) -> None:
    """Add an entry to a collection, only once.

    Examples:

        >>> l = []
        >>> _add_once(l, {'foo': []})
        >>> l
        [{'foo': []}]

        >>> _add_once(l, {'foo': []})
        >>> l
        [{'foo': []}]

    Args:
        coll:
        to_add:

    Returns:

    """
    if to_add in coll:
        return None

    coll.append(to_add)
    return None


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
