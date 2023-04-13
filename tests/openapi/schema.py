#!/usr/bin/env python3
# Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import os
from re import match
from typing import Any

import schemathesis
from schemathesis import auths as schemathesis_auth

from tests.testlib.site import get_site_factory, Site
from tests.testlib.utils import current_base_branch_name

from tests.openapi import settings

logger = logging.getLogger(__name__)

sample_style = "curl"
skip_deprecated = True


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

    if "CMK-12220" in settings.suppressed_issues:
        update_schema(
            raw_schema,
            "properties",
            {"format": "string", "pattern": "^[a-zA-Z0-9][a-zA-Z0-9_-]+$"},
            {
                "type": "string",
                "format": None,
                "enum": None,
                "pattern": "[a-zA-Z0-9][a-zA-Z0-9_-]+",
            },
            True,
        )


def add_links(
    schema: schemathesis.specs.openapi.schemas.BaseOpenAPISchema,
) -> schemathesis.specs.openapi.schemas.BaseOpenAPISchema:
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
        property_id = src_schema.get("required", list(src_schema["properties"].keys()))[0]
        property_pattern = src_schema["properties"][property_id].get("pattern", None)
        parameter = endpoint["target"].split("{", 1)[-1].split("}", 1)[0]

        for method in endpoint["methods"]:
            trg_schema = raw_schema["paths"][endpoint["target"]][method.lower()]
            parameter_pattern = trg_schema["parameters"][0]["schema"].get("pattern", None)

            if (
                parameter_pattern
                and not property_pattern
                and "CMK-12182" not in settings.suppressed_issues
            ):
                logger.error(
                    '%s %s: Parameter pattern "%s" defined while POST %s object property'
                    ' "%s" has no pattern!',
                    method,
                    endpoint["target"],
                    parameter_pattern,
                    endpoint["source"],
                    property_id,
                )
            elif parameter_pattern and parameter_pattern != property_pattern:
                logger.warning(
                    '%s %s: Parameter pattern "%s" defined while POST %s object property'
                    ' "%s" has a different pattern!',
                    method,
                    endpoint["target"],
                    parameter_pattern,
                    endpoint["source"],
                    property_id,
                )
            schema.add_link(
                source=schema[endpoint["source"]]["POST"],
                target=schema[endpoint["target"]][method],
                status_code="200",
                parameters={parameter: "$response.body#/id"},
            )
    return schema


def get_crud_endpoints(
    schema: schemathesis.specs.openapi.schemas.BaseOpenAPISchema,
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
        and match(f"/objects/{object_type}/{{[^}}/]*}}(\\?.*)?$", target)
        and (target_methods := set(map(str.lower, methods)).intersection(schema[target]))
        and (accept is None or match(accept, object_type))
        and (ignore is None or not match(ignore, object_type))
    ]


def get_schema() -> schemathesis.specs.openapi.schemas.BaseOpenAPISchema:
    """Return schema for parametrization."""
    site = get_site()
    token = f"Bearer automation {site.get_automation_secret()}"

    @schemathesis_auth.register()
    class _Auth(schemathesis_auth.AuthProvider):
        """Default authentication provider."""

        def get(self, context):
            return token

        def set(self, case, data, context):
            case.cookies = {}
            case.headers["Authorization"] = token
            case.headers["Content-Type"] = "application/json"

    site_id = site.id
    api_url = f"http://localhost/{site_id}/check_mk/api/1.0"
    schema_filename = "openapi-swagger-ui"
    schema_filedir = os.getenv("TEST_OPENAPI_SCHEMA_DIR", os.getenv("HOME"))
    if os.path.exists(f"{schema_filedir}/{schema_filename}.json"):
        schema_filetype = "json"
    else:
        schema_filetype = "yaml"
    schema_filepath = f"{schema_filedir}/{schema_filename}.{schema_filetype}"
    schema_url = f"{api_url}/{schema_filename}.{schema_filetype}"
    if os.path.exists(schema_filepath):
        logger.info('Loading OpenAPI schema from file "%s"...', schema_filepath)
        schema = schemathesis.from_path(
            schema_filepath,
            base_url=api_url,
            skip_deprecated_operations=skip_deprecated,
            code_sample_style=sample_style,
        )
    else:
        logger.info('Loading OpenAPI schema from URL "%s"...', schema_url)
        schema = schemathesis.from_uri(
            schema_url,
            base_url=api_url,
            skip_deprecated_operations=skip_deprecated,
            headers={"Authorization": token},
            code_sample_style=sample_style,
        )
    schema = add_links(schema)

    # IGNORE /objects/rule/{rule_id}/actions/move/invoke
    # To avoid a failure during parametrization for this endpoint, we are deprecating it
    schema.raw_schema["paths"]["/objects/rule/{rule_id}/actions/move/invoke"]["post"].update(
        {"deprecated": True}
    )

    return schema


def get_site() -> Site:
    logger.info("Setting up testsite")
    sf = get_site_factory(
        prefix="openapi_",
        install_test_python_modules=False,
        fallback_branch=current_base_branch_name,
    )
    site_to_return = sf.get_existing_site("central")
    if site_to_return.exists():
        if not site_to_return.is_running():
            site_to_return.start()
        logger.info("Reuse existing site")
    else:
        logger.info("Creating new site")
        site_to_return = sf.get_site("central")
    logger.info("Testsite %s is up", site_to_return.id)

    return site_to_return


def parametrize_crud_endpoints(
    schema: schemathesis.specs.openapi.schemas.BaseOpenAPISchema,
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
    property_data: dict[str, Any],
    ticket_id: str | None = None,
    merge: bool = True,
) -> None:
    if ticket_id and ticket_id not in settings.suppressed_issues:
        return
    schema_data = raw_schema["components"]["schemas"][schema_name]["properties"][property_name]
    for key in property_data:
        if key not in schema_data or not isinstance(schema_data[key], (dict, list)):
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
    if ticket_id and ticket_id not in settings.suppressed_issues:
        return
    if "required" not in raw_schema["components"]["schemas"][schema_name]:
        raw_schema["components"]["schemas"][schema_name]["required"] = []
    required_properties = raw_schema["components"]["schemas"][schema_name]["required"]
    if merge:
        for property_name in [_ for _ in properties if _ not in required_properties]:
            logger.warning(
                'SCHEMA %s: Property "%s" is not required but expected.%s',
                schema_name,
                property_name,
                f" #{ticket_id}" if ticket_id else "",
            )
            required_properties.append(property_name)
    else:
        required_properties = properties


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
    del_values = (key for key in patch.keys() if key is None) if delete_nulls else ()
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
            else:
                if matching_dict(raw_schema[key], expected):
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
