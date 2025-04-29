#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
import logging
from typing import Any

import requests
import schemathesis
import schemathesis.transports.responses
from requests.structures import CaseInsensitiveDict

from tests.schemathesis_openapi import settings
from tests.schemathesis_openapi.response import fix_response, PROBLEM_CONTENT_TYPE
from tests.schemathesis_openapi.schema import (
    add_formats_and_patterns,
    require_properties,
    update_property,
)

logger = logging.getLogger(__name__)


@schemathesis.hook("before_load_schema")
def hook_before_load_schema(
    context: schemathesis.hooks.HookContext, raw_schema: dict[str, Any]
) -> None:
    """Modify the raw schema before loading it.

    This can be used to suppress known schema issues that would affect test data generation
    (e.g. define value patterns, add required properties or define response status codes).
    """
    logger.debug("INIT: before_load_schema handler")

    # save the unchanged schema to a temporary file
    with open("/tmp/schema.json", "w") as f:
        json.dump(raw_schema, f, indent=2)

    # SCHEMA modifications
    require_properties(raw_schema, "InputRuleObject", ["raw_value", "conditions"], None)
    require_properties(raw_schema, "CheckboxWithStrValue", ["state"], None, merge=False)
    require_properties(raw_schema, "NotificationBulkingCheckbox", ["state"], None, merge=False)

    update_property(
        raw_schema,
        "HostViewAttribute",
        "snmp_community",
        {"nullable": True},
        None,
    )

    for schema_name in (
        "FolderUpdateAttribute",
        "FolderViewAttribute",
        "FolderCreateAttribute",
        "HostViewAttribute",
        "HostCreateAttribute",
        "HostUpdateAttribute",
        "ClusterCreateAttribute",
    ):
        update_property(
            raw_schema,
            schema_name,
            "management_ipmi_credentials",
            {"nullable": True},
            None,
        )

    if "CMK-21783" in settings.suppressed_issues:
        raw_schema["components"]["schemas"]["InventoryPaths"]["anyOf"] = raw_schema["components"][
            "schemas"
        ]["InventoryPaths"].pop("oneOf")
    # ignore invalid time range values
    update_property(raw_schema, "TimeRange2", "start", {"format": "binary"}, None)
    update_property(raw_schema, "TimeRange2", "end", {"format": "binary"}, None)
    update_property(raw_schema, "ConcreteTimeRange", "start", {"format": "binary"}, None)
    update_property(raw_schema, "ConcreteTimeRange", "end", {"format": "binary"}, None)

    # SCHEMA modifications: additionalProperties
    # control the creation of additionalProperties in the root level of schema object definitions:
    # * do not allow any additionalProperties by default
    # * make sure additionalProperties of type "string" match the default string pattern
    schemas = raw_schema["components"]["schemas"]
    for schema_name in [
        _
        for _ in schemas
        if _
        not in (
            "HostConfig",
            "CollectionItem",
            "RulesetCollection",
            "Link",
        )
    ]:
        if not set(schemas[schema_name]).intersection(
            ("additionalProperties", "oneOf", "anyOf", "allOf", "not")
        ):
            schemas[schema_name]["additionalProperties"] = False
        elif (
            "additionalProperties" in schemas[schema_name]
            and isinstance(schemas[schema_name]["additionalProperties"], dict)
            and schemas[schema_name]["additionalProperties"].get("type") == "string"
            and not schemas[schema_name]["additionalProperties"].get("pattern")
        ):
            schemas[schema_name]["additionalProperties"]["pattern"] = (
                settings.default_string_pattern
            )

    # PATH modifications
    # ignore some endpoints (via deprecating them) to avoid failures during parametrization
    for path, methods in {
        "/objects/rule/{rule_id}/actions/move/invoke": ("post",),
        "/objects/bi_rule/{rule_id}": ("post", "put"),
        "/objects/notification_rule/{rule_id}": ("put",),
        "/objects/notification_rule/{rule_id}/actions/delete/invoke": ("post",),
        "/domain-types/rule/collections/all": ("post",),
        "/domain-types/metric/actions/filter/invoke": ("post",),  # internal endpoint
    }.items():
        for method in methods:
            raw_schema["paths"][path][method].update({"deprecated": True})

    add_formats_and_patterns(raw_schema)

    # save the update schema to a temporary file
    with open("/tmp/schema.updated.json", "w") as f:
        json.dump(raw_schema, f, indent=2)


@schemathesis.hook("before_call")
def hook_before_call(
    context: schemathesis.hooks.HookContext,
    case: schemathesis.models.Case,
) -> None:
    """Modify the case before execution.

    This can be used to override the headers or other generic properties.
    """
    logger.debug("%s %s: before_call handler", case.method, case.path)
    if case.headers is None:
        case.headers = CaseInsensitiveDict({})
    case.headers["Content-Type"] = "application/json"
    case.headers["If-Match"] = "*"


@schemathesis.hook("after_call")
def hook_after_call(
    context: schemathesis.hooks.HookContext,
    case: schemathesis.models.Case,
    response: schemathesis.transports.responses.GenericResponse,
) -> None:
    """Modify the case response after execution but before validation.

    This can be used to analyze and modify the response before validation
    (e.g. to suppress response validation errors).
    """
    after_call(case, response)


def after_call(
    case: schemathesis.models.Case,
    response: schemathesis.transports.responses.GenericResponse,
) -> schemathesis.transports.responses.GenericResponse:
    logger.debug("%s %s: after_call handler", case.method, case.path)
    reason = response.reason if isinstance(response, requests.Response) else "n/a"

    if case.path in (
        "/domain-types/agent/actions/download/invoke",
        "/domain-types/agent/actions/download_by_hash/invoke",
        "/domain-types/agent/actions/download_by_host/invoke",
    ):
        # generic: invalid agent download response Content-Type
        fix_response(
            case,
            response,
            status_code=200,
            update_headers=CaseInsensitiveDict({"Content-Type": "application/octet-stream"}),
            ticket_id=None,
        )
    if case.path == "/domain-types/licensing/actions/configure/invoke":
        fix_response(
            case,
            response,
            status_code=-204,
            valid_body=False,
            body={},
            set_body={"links": []},
            ticket_id=None,
        )
    # generic: invalid JSON response
    fix_response(
        case,
        response,
        status_code=-204,
        valid_body=False,
        body={},
        set_body={
            "title": reason,
            "status": response.status_code,
            "detail": reason,
        },
        ticket_id="CMK-11886",
    )

    fix_response(
        case,
        response,
        "POST",
        "/domain-types/host_config/actions/bulk-create/invoke",
        body={},
        update_items={"value": {"links": []}},
        ticket_id=None,
    )
    fix_response(
        case,
        response,
        "PUT",
        "/domain-types/host_config/actions/bulk-update/invoke",
        body={},
        update_items={"value": {"links": []}},
        ticket_id=None,
    )
    fix_response(
        case,
        response,
        "GET",
        "/domain-types/host_config/collections/all",
        body={},
        update_items={"value": {"links": []}},
        ticket_id=None,
    )
    # avoid validation error if the "links" property is not selected to be returned
    # NOTE: the "links" property is marked as *required* in the response schema
    fix_response(
        case,
        response,
        "GET",
        "/domain-types/host_config/collections/all",
        body={"links": None},
        update_items={"links": []},
        ticket_id=None,
    )

    # generic: empty response Content-Type
    fix_response(
        case,
        response,
        empty_content_type=True,
        valid_content_type=False,
        update_headers=CaseInsensitiveDict({"Content-Type": "{auto}"}),
        ticket_id="CMK-11886",
    )
    # generic: invalid (but not empty) response Content-Type
    fix_response(
        case,
        response,
        empty_content_type=False,
        valid_content_type=False,
        update_headers=CaseInsensitiveDict({"Content-Type": "{auto}"}),
        ticket_id="CMK-11886",
    )
    # generic: invalid 404 response Content-Type
    try:
        response.json
    except json.decoder.JSONDecodeError:
        # in case the body is not valid json, replace it
        _404_body: dict[str, Any] | None = {
            "title": "Not Found",
            "status": 404,
            "detail": str(response.content),
        }
    else:
        _404_body = None
    fix_response(
        case,
        response,
        status_code=404,
        update_headers=CaseInsensitiveDict({"Content-Type": PROBLEM_CONTENT_TYPE}),
        set_body=_404_body,
        ticket_id="CMK-11886",
    )
    # generic: invalid 400 response Content-Type
    fix_response(
        case,
        response,
        status_code=400,
        update_headers=CaseInsensitiveDict({"Content-Type": PROBLEM_CONTENT_TYPE}),
        ticket_id=None,
    )

    # incomplete 200 responses
    fix_response(
        case,
        response,
        method="GET",
        path="/objects/ruleset/{ruleset_name}",
        status_code=200,
        update_body={"extensions": {"folder": "/"}},
        ticket_id=None,
    )
    fix_response(
        case,
        response,
        method="GET",
        path="/domain-types/[^/]+/collections/all",
        status_code=200,
        valid_body=True,
        object_type="ruleset",
        update_items={
            "value": {"href": "", "method": "GET", "rel": "", "type": "application/json"}
        },
        ticket_id=None,
    )

    # invalid status: 500 instead of 400
    fix_response(
        case,
        response,
        method="POST",
        path="/domain-types/metric/actions/filter/invoke",
        status_code=500,
        body={"detail": "There is no graph template with the id .*"},
        set_status_code=400,
        update_body={"title": "Bad Request", "status": 400},
        ticket_id=None,
    )
    fix_response(
        case,
        response,
        method="POST",
        path="/objects/bi_rule/{rule_id}",
        status_code=500,
        body={"detail": "The requested pack_id does not exist"},
        set_status_code=400,
        update_body={"title": "Not Found", "status": 400},
        ticket_id="CMK-21677",
    )
    fix_response(
        case,
        response,
        method="PUT",
        path="/objects/bi_rule/{rule_id}",
        status_code=500,
        body={"detail": "The requested pack_id does not exist"},
        set_status_code=400,
        update_body={"title": "Bad Request", "status": 400},
        ticket_id="CMK-21677",
    )
    fix_response(
        case,
        response,
        method="GET",
        path="/objects/notification_rule/{rule_id}",
        status_code=404,
        set_body={
            "title": "Not Found",
            "detail": "The requested rule_id does not exist",
            "status": 404,
        },
        ticket_id="CMK-21807",
    )
    fix_response(
        case,
        response,
        method="GET",
        path="/objects/quick_setup_action_result/{job_id}",
        status_code=400,
        set_status_code=404,
        set_body={"status": 404},
        ticket_id="CMK-21809",
    )
    fix_response(
        case,
        response,
        method="GET",
        path="/objects/quick_setup_stage_action_result/{job_id}",
        status_code=400,
        set_status_code=404,
        set_body={"status": 404},
        ticket_id="CMK-21809",
    )

    return response
