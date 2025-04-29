#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import os
from collections.abc import Iterator
from re import match
from typing import Any

import schemathesis
from requests.structures import CaseInsensitiveDict
from schemathesis import DataGenerationMethod
from schemathesis.generation import GenerationConfig
from schemathesis.specs.openapi import schemas

from tests.testlib.site import AUTOMATION_USER, get_site_factory, Site

from tests.schemathesis_openapi import settings

logger = logging.getLogger(__name__)

skip_deprecated_operations = True
validate_schema = True
data_generation_methods = (DataGenerationMethod.positive,)
code_sample_style = "curl"


def add_formats_and_patterns(raw_schema: dict[str, Any]) -> None:
    """Set format "string" for any properties which are of type "string" and have no format, enum or pattern defined.

    Override pattern for any properties which have an invalid default pattern.
    """
    # define default generic string pattern
    update_schema(
        raw_schema,
        "properties",
        {"format": "string"},
        {"type": "string", "format": None, "enum": None, "pattern": None},
        True,
    )
    update_schema(
        raw_schema,
        "properties",
        {"format": "string", "pattern": None},
        {"type": "string", "format": None, "enum": None, "pattern": "[^/]+"},
        True,
    )
    update_schema(
        raw_schema,
        "properties",
        {"format": "string", "pattern": "^[-a-z0-9A-Z_]+$"},
        {"type": "string", "format": None, "enum": None, "pattern": "^[-a-z0-9A-Z_]*$"},
        True,
    )
    update_schema(
        raw_schema,
        "properties",
        {
            "format": "string",
            "pattern": "^(all|monday|tuesday|wednesday|thursday|friday|saturday|sunday)$",
        },
        {
            "type": "string",
            "format": None,
            "enum": None,
            "pattern": "all|monday|tuesday|wednesday|thursday|friday|saturday|sunday",
        },
        True,
    )
    update_schema(
        raw_schema,
        "properties",
        {
            "format": "string",
            "pattern": "^(monday|tuesday|wednesday|thursday|friday|saturday|sunday)$",
        },
        {
            "type": "string",
            "format": None,
            "enum": None,
            "pattern": "monday|tuesday|wednesday|thursday|friday|saturday|sunday",
        },
        True,
    )


def add_links(
    schema: schemas.BaseOpenAPISchema,
) -> schemas.BaseOpenAPISchema:
    """Define required API links.

    Link POST requests to dependent GET/PUT/PATCH/DELETE or POST requests.
    """
    raw_schema = schema.raw_schema
    for endpoint in get_crud_endpoints(schema):
        src_schema_ref = raw_schema["paths"][endpoint["source"]]["post"]["requestBody"]["content"][
            "application/json"
        ]["schema"]["$ref"]
        src_schema = raw_schema
        for key in src_schema_ref[2:].split("/"):
            src_schema = src_schema[key]
        if not (property_ids := src_schema.get("required", list(src_schema["properties"].keys()))):
            continue
        property_id = property_ids[0]
        property_pattern = src_schema["properties"][property_id].get("pattern", None)
        parameter = endpoint["target"].split("{", 1)[-1].split("}", 1)[0]

        for method in endpoint["methods"]:
            trg_schema = raw_schema["paths"][endpoint["target"]][method.lower()]
            parameter_pattern = trg_schema["parameters"][0]["schema"].get("pattern", None)

            if parameter_pattern and not property_pattern:
                logger.error(
                    '%s %s: Parameter pattern "%s" defined while POST %s object property'
                    ' "%s" has no pattern!',
                    method.upper(),
                    endpoint["target"],
                    parameter_pattern,
                    endpoint["source"],
                    property_id,
                )
            elif parameter_pattern and parameter_pattern != property_pattern:
                logger.warning(
                    '%s %s: Parameter pattern "%s" defined while POST %s object property'
                    ' "%s" has a different pattern "%s"!',
                    method.upper(),
                    endpoint["target"],
                    parameter_pattern,
                    endpoint["source"],
                    property_id,
                    property_pattern,
                )
            schema.add_link(
                source=schema[endpoint["source"]]["POST"],
                target=schema[endpoint["target"]][method],
                status_code="200",
                parameters={parameter: "$response.body#/id"},
            )
    return schema


def get_crud_endpoints(
    schema: schemas.BaseOpenAPISchema,
    accept: str | None = None,
    ignore: str | None = None,
    methods: tuple[str, ...] = ("get", "put", "patch", "delete"),
) -> list[dict[str, Any]]:
    """Auto-detect relations between POST and GET/PUT/PATCH/DELETE requests."""
    return [
        {
            "type": object_type,
            "source": source,
            "target": target,
            "methods": target_methods,
        }
        for target in schema
        for source in sorted(
            {
                path
                for path in schema
                if match("/domain-types/[^/]*/collections/all", path) and "POST" in schema[path]
            }
        )
        if (object_type := source.split("/", 3)[:3][-1])
        and object_type not in ("notification_rule")
        and match(f"/objects/{object_type}/{{[^}}/]*}}(\\?.*)?$", target)
        and (target_methods := set(map(str.lower, methods)).intersection(schema[target]))
        and (accept is None or match(accept, object_type))
        and (ignore is None or not match(ignore, object_type))
    ]


def get_site() -> Iterator[Site]:
    yield from get_site_factory(prefix="openapi_").get_test_site("central", auto_cleanup=False)


def get_schema() -> schemas.BaseOpenAPISchema:
    """Return schema for parametrization."""
    site = next(get_site())

    token = f"Bearer {AUTOMATION_USER} {site.get_automation_secret()}"

    @schemathesis.auths.register()
    class _Auth(schemathesis.auths.AuthProvider):
        """Default authentication provider."""

        def get(self, case, context):
            return token

        def set(self, case, data, context):
            case.cookies = {}
            if case.headers is None:
                case.headers = CaseInsensitiveDict({})
            case.headers["Authorization"] = token
            case.headers["Content-Type"] = "application/json"

    api_url = f"http://localhost:{site.apache_port}/{site.id}/check_mk/api/1.0"
    schema_filename = "openapi-doc"
    schema_filedir = os.getenv("SCHEMATHESIS_SCHEMA_DIR", "")
    if os.path.exists(f"{schema_filedir}/{schema_filename}.json"):
        schema_filetype = "json"
    else:
        schema_filetype = "yaml"
    schema_filepath = f"{schema_filedir}/{schema_filename}.{schema_filetype}"
    schema_url = f"{api_url}/{schema_filename}.{schema_filetype}"
    allow_nulls = os.getenv("SCHEMATHESIS_ALLOW_NULLS", "0") == "1"
    codec = os.getenv("SCHEMATHESIS_CODEC", "utf-8")
    generation_config = GenerationConfig(allow_x00=allow_nulls, codec=codec)
    schemathesis.experimental.OPEN_API_3_1.enable()
    if os.path.exists(schema_filepath):
        logger.info('Loading OpenAPI schema from file "%s"...', schema_filepath)
        schema = schemathesis.from_path(
            schema_filepath,
            base_url=api_url,
            skip_deprecated_operations=skip_deprecated_operations,
            validate_schema=validate_schema,
            data_generation_methods=data_generation_methods,
            code_sample_style=code_sample_style,
            generation_config=generation_config,
        )
    else:
        logger.info('Loading OpenAPI schema from URL "%s"...', schema_url)
        # NOTE: We need to pass the Auth token to retrieve the schema via URL,
        # since the AuthProvider will not be used during schema initialization!
        schema = schemathesis.from_uri(
            schema_url,
            base_url=api_url,
            skip_deprecated_operations=skip_deprecated_operations,
            validate_schema=validate_schema,
            data_generation_methods=data_generation_methods,
            code_sample_style=code_sample_style,
            generation_config=generation_config,
            headers={"Authorization": token},
        )
    schema = add_links(schema)

    return schema


def parametrize_crud_endpoints(
    schema: schemas.BaseOpenAPISchema,
    accept: str | None = None,
    ignore: str | None = None,
) -> dict[str, Any]:
    """Parametrization helper to generate individual CRUD tests named after the object type."""
    endpoints = get_crud_endpoints(schema, accept, ignore)
    return {"argvalues": endpoints, "ids": [endpoint["type"] for endpoint in endpoints]}


def update_property(
    raw_schema: dict[str, Any],
    schema_name: str,
    property_name: str,
    property_data: dict[str, Any] | None = None,
    ticket_id: str | None = None,
    merge: bool = True,
) -> None:
    """Update a property in the schema to suppress a specific problem."""
    if ticket_id and ticket_id not in settings.suppressed_issues:
        return
    schema_data = (
        raw_schema["components"]["schemas"]
        .get(schema_name, {})
        .get("properties", {})
        .get(property_name)
    )
    if schema_data is None:
        logger.warning("SCHEMA %s: Schema not found!", schema_name)
        return
    if property_data is None:
        del schema_data
        return
    for key in property_data:
        if key not in schema_data or not isinstance(schema_data[key], dict | list):
            schema_data[key] = property_data[key]
            logger.warning(
                'SCHEMA %s: Property "%s" must be defined as "%s".%s',
                schema_name,
                property_name,
                property_data[key],
                f" #{ticket_id}" if ticket_id else "",
            )
        elif merge and property_data[key] != schema_data[key]:
            if isinstance(schema_data[key], list):
                if isinstance(property_data[key], list):
                    schema_data[key] += property_data[key]
                else:
                    schema_data[key].append(property_data[key])
            elif isinstance(property_data[key], dict):
                schema_data[key].update(property_data[key])
            else:
                continue
            logger.warning(
                'SCHEMA %s: Property "%s" must be updated with "%s".%s',
                schema_name,
                property_name,
                property_data[key],
                f" #{ticket_id}" if ticket_id else "",
            )


def require_properties(
    raw_schema: dict[str, Any],
    schema_name: str,
    properties: list[str],
    ticket_id: str | None = None,
    merge: bool = True,
) -> None:
    """Require one ore more properties in the schema to suppress a specific bug."""
    if ticket_id and ticket_id not in settings.suppressed_issues:
        return
    if "required" not in raw_schema["components"]["schemas"][schema_name]:
        raw_schema["components"]["schemas"][schema_name]["required"] = []
    required_properties: list = raw_schema["components"]["schemas"][schema_name]["required"]
    if not merge:
        for property_name in [_ for _ in required_properties if _ not in properties]:
            logger.warning(
                'SCHEMA %s: Property "%s" is required but not expected to be.%s',
                schema_name,
                property_name,
                f" #{ticket_id}" if ticket_id else "",
            )
            required_properties.remove(property_name)
    for property_name in [_ for _ in properties if _ not in required_properties]:
        logger.warning(
            'SCHEMA %s: Property "%s" is not required but expected to be.%s',
            schema_name,
            property_name,
            f" #{ticket_id}" if ticket_id else "",
        )
        required_properties.append(property_name)


def update_schema(
    raw_schema: dict[str, Any],
    key_name: str,
    patch: dict[str, Any],
    expected: dict[str, Any] | None = None,
    update_children: bool = True,
    delete_nulls: bool = True,
    path: str = "",
) -> None:
    """Update all matching keys of a raw_schema dictionary recursively.

    Can be used for generic patching of matching schema objects.
    """

    def matching_dict(raw_schema: dict[str, Any], expected: dict[str, Any] | None) -> bool:
        """Return True if all expected values are found in the object."""
        return expected is None or all(
            raw_schema.get(attribute) == expected[attribute] for attribute in expected
        )

    upd_values = {key: val for key, val in patch.items() if val is not None}
    del_values = patch.keys() if delete_nulls else ()
    keys = [key for key in raw_schema if isinstance(raw_schema[key], dict)]
    for key in keys:
        key_path = f"{path}/{key}"
        if key == key_name:
            if update_children:
                children = [
                    child
                    for child in raw_schema[key]
                    if isinstance(raw_schema[key][child], dict)
                    and matching_dict(raw_schema[key][child], expected)
                ]
                for child in children:
                    logger.debug('Patching path "%s/%s" with %s', key_path, child, upd_values)
                    raw_schema[key][child].update(upd_values)
                    for val in del_values:
                        raw_schema[key][child].pop(val, None)
            elif matching_dict(raw_schema[key], expected):
                logger.debug('Patching path "%s" with %s', key_path, upd_values)
                raw_schema[key].update(upd_values)
                for val in del_values:
                    raw_schema[key].pop(val, None)
        else:
            update_schema(
                raw_schema[key],
                key_name,
                patch,
                expected,
                update_children,
                delete_nulls,
                key_path,
            )
