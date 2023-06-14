#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
from typing import Any

import schemathesis
from requests.structures import CaseInsensitiveDict

from tests.openapi import settings
from tests.openapi.response import fix_response, problem_response
from tests.openapi.schema import add_formats_and_patterns, require_properties, update_property

logger = logging.getLogger(__name__)


@schemathesis.hooks.register("before_load_schema")
def hook_before_load_schema(  # pylint: disable=too-many-branches
    context: schemathesis.hooks.HookContext, raw_schema: dict[str, Any]
) -> None:
    """Modify the raw schema before loading it.

    This can be used to suppress known schema issues that would affect test data generation
    (e.g. define value patterns, add required properties or define response status codes).
    """
    logger.debug("INIT: before_load_schema handler")

    # SCHEMA modifications
    require_properties(raw_schema, "TimeRangeActive", ["day", "time_ranges"], "CMK-12181")
    require_properties(raw_schema, "TimeAllowedRange", ["start", "end"], "CMK-12235")
    require_properties(raw_schema, "InputRuleObject", ["raw_value", "conditions"], "CMK-RULE")

    require_properties(raw_schema, "InputServiceGroup", ["alias"], "CMK-12334")

    require_properties(raw_schema, "BulkInputContactGroup", ["entries"], "CMK-12327")
    require_properties(raw_schema, "BulkUpdateContactGroup", ["entries"], "CMK-12327")
    require_properties(raw_schema, "BulkUpdateFolder", ["entries"], "CMK-12327")
    require_properties(raw_schema, "BulkCreateHost", ["entries"], "CMK-12327")
    require_properties(raw_schema, "BulkUpdateHost", ["entries"], "CMK-12327")
    require_properties(raw_schema, "BulkInputHostGroup", ["entries"], "CMK-12327")
    require_properties(raw_schema, "BulkUpdateHostGroup", ["entries"], "CMK-12327")
    require_properties(raw_schema, "BulkInputServiceGroup", ["entries"], "CMK-12327")
    require_properties(raw_schema, "BulkUpdateServiceGroup", ["entries"], "CMK-12327")

    update_property(raw_schema, "BulkInputContactGroup", "entries", {"minItems": 1}, "CMK-12327")
    update_property(raw_schema, "BulkUpdateContactGroup", "entries", {"minItems": 1}, "CMK-12327")
    update_property(raw_schema, "BulkUpdateFolder", "entries", {"minItems": 1}, "CMK-12327")
    update_property(raw_schema, "BulkCreateHost", "entries", {"minItems": 1}, "CMK-12327")
    update_property(raw_schema, "BulkUpdateHost", "entries", {"minItems": 1}, "CMK-12327")
    update_property(raw_schema, "BulkInputHostGroup", "entries", {"minItems": 1}, "CMK-12327")
    update_property(raw_schema, "BulkUpdateHostGroup", "entries", {"minItems": 1}, "CMK-12327")
    update_property(raw_schema, "BulkInputServiceGroup", "entries", {"minItems": 1}, "CMK-12327")
    update_property(raw_schema, "BulkUpdateServiceGroup", "entries", {"minItems": 1}, "CMK-12327")

    update_property(raw_schema, "BulkDeleteContactGroup", "entries", {"minItems": 1}, "CMK-12327")
    update_property(raw_schema, "BulkDeleteHost", "entries", {"minItems": 1}, "CMK-12327")
    update_property(raw_schema, "BulkDeleteHostGroup", "entries", {"minItems": 1}, "CMK-12327")
    update_property(raw_schema, "BulkDeleteServiceGroup", "entries", {"minItems": 1}, "CMK-12327")

    update_property(
        raw_schema,
        "CreateUser",
        "username",
        {"pattern": settings.default_identifier_pattern},
        "CMK-11859",
    )

    update_property(raw_schema, "InputHostTagGroup", "tags", {"minItems": 1}, "CMK-12048")
    update_property(raw_schema, "UpdateHostTagGroup", "tags", {"minItems": 1}, "CMK-12048")

    update_property(
        raw_schema,
        "TimeAllowedRange",
        "start",
        {"pattern": "^[0-9][0-9]:[0-9][0-9](:[0-9][0-9])?$"},
        "CMK-12235",
    )
    update_property(
        raw_schema,
        "TimeAllowedRange",
        "end",
        {"pattern": "^[0-9][0-9]:[0-9][0-9](:[0-9][0-9])?$"},
        "CMK-12235",
    )

    name_pattern = "^[a-zA-Z0-9][a-zA-Z0-9_-]+$"
    for schema_name in (
        "InputContactGroup",
        "InputHostGroup",
        "InputServiceGroup",
        "CreateTimePeriod",
    ):
        update_property(raw_schema, schema_name, "name", {"pattern": name_pattern}, "CMK-12182")
    # see CMK-12217 as well
    update_property(raw_schema, "InputPassword", "ident", {"pattern": name_pattern}, "CMK-12182")

    update_property(
        raw_schema,
        "InputHostTagGroup",
        "ident",
        {"pattern": "^[a-zA-Z_]+[-0-9a-zA-Z_]$"},
        "CMK-12182",
    )

    # NOTE: We do not really want "user_id" to be nullable,
    # but it is way simpler to suppress the issue like that!
    update_property(raw_schema, "ChangesFields", "user_id", {"nullable": True}, "CMK-12380")

    # SCHEMA modifications: additionalProperties
    # control the creation of additionalProperties in the root level of schema object definitions:
    # * do not allow any additionalProperties by default
    # * make sure additionalProperties of type "string" match the default string pattern
    schemas = raw_schema["components"]["schemas"]
    for schema_name in [
        _ for _ in schemas if _ not in ("CollectionItem", "RulesetCollection", "Link")
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
            schemas[schema_name]["additionalProperties"][
                "pattern"
            ] = settings.default_string_pattern

    # PATH modifications
    paths = raw_schema["paths"]
    if "CMK-12241" in settings.suppressed_issues:
        paths["/objects/time_period/{name}"]["delete"]["parameters"] = [
            parm
            for parm in paths["/objects/time_period/{name}"]["delete"]["parameters"]
            if parm["name"] != "If-Match"
        ]
    for endpoint in [
        {"path": _path, "method": _method} for _path in paths for _method in paths[_path]
    ]:
        path = endpoint["path"]
        method = endpoint["method"].lower()
        responses = paths[path][method]["responses"]
        if "UNDEFINED-HTTP500" in settings.suppressed_issues and not set(responses).intersection(
            {"5XX", "500"}
        ):
            logger.warning(
                "%s %s: Suppressed undefined status code 500! #UNDEFINED-HTTP500",
                method.upper(),
                path,
            )
            responses.update(problem_response("500", "Internal Server Error"))
        if "CMK-11924" in settings.suppressed_issues:
            if not set(responses).intersection({"4XX", "400"}):
                logger.warning(
                    "%s %s: Suppressed undefined status code 400! #CMK-11924",
                    method.upper(),
                    path,
                )
                responses.update(problem_response("400", "Bad request"))
            if method == "get" and not "404" in responses:
                logger.warning(
                    "%s %s: Suppressed undefined status code 404! #CMK-11924",
                    method.upper(),
                    path,
                )
                responses.update(problem_response("404", "Not found"))
    if "CMK-12246" in settings.suppressed_issues:
        paths["/domain-types/agent/actions/bake/invoke"]["post"]["responses"].update(
            problem_response("409", "Conflict")
        )
    if "CMK-12421" in settings.suppressed_issues:
        paths["/domain-types/activation_run/actions/activate-changes/invoke"]["post"][
            "responses"
        ].update(problem_response("204", "No Content"))

    add_formats_and_patterns(raw_schema)


@schemathesis.hooks.register("before_call")
def hook_before_call(
    context: schemathesis.hooks.HookContext,
    case: schemathesis.Case,
) -> None:
    """Modify the case before execution.

    This can be used to override the headers or other generic properties.
    """
    logger.debug("%s %s: before_call handler", case.method, case.path)
    if case.headers is None:
        case.headers = CaseInsensitiveDict({})
    case.headers["Content-Type"] = "application/json"


@schemathesis.hooks.register("after_call")
def hook_after_call(  # pylint: disable=too-many-branches
    context: schemathesis.hooks.HookContext,
    case: schemathesis.Case,
    response: schemathesis.GenericResponse,
) -> None:
    """Modify the case after execution but before validation.

    This can be used to analyze and modify the response before validation
    (e.g. to suppress response validation errors).
    """
    logger.debug("%s %s: after_call handler", case.method, case.path)

    # generic: invalid JSON response
    fix_response(
        case,
        response,
        status_code=-204,
        valid_body=False,
        body={},
        set_body={
            "title": response.reason,
            "status": response.status_code,
            "detail": response.reason,
        },
        ticket_id="INVALID-JSON",
    )

    # generic: empty response Content-Type
    fix_response(
        case,
        response,
        empty_content_type=True,
        valid_content_type=False,
        update_headers={"Content-Type": "{auto}"},
        ticket_id="CMK-11886",
    )
    # generic: invalid (but not empty) response Content-Type
    fix_response(
        case,
        response,
        empty_content_type=False,
        valid_content_type=False,
        update_headers={"Content-Type": "{auto}"},
        ticket_id="CMK-11886",
    )

    # incomplete 200 responses
    fix_response(
        case,
        response,
        method="POST",
        path="/domain-types/time_period/collections/all",
        status_code=200,
        body={},
        valid_body=True,
        set_body={
            "links": [],
            "domainType": "",
        },
        ticket_id="CMK-12044",
    )
    fix_response(
        case,
        response,
        method="POST",
        path="/domain-types/password/collections/all",
        status_code=200,
        update_body={"extensions": {"password": "********"}},
        ticket_id="CMK-TODO",
    )
    fix_response(
        case,
        response,
        method="GET",
        path="/objects/ruleset/{ruleset_name}",
        status_code=200,
        update_body={"extensions": {"folder": "/"}},
        ticket_id="CMK-RULE",
    )
    invalid_link_issues = {
        "CMK-12140": "time_period",
        "CMK-12143": "agent",
        "CMK-12144": "password",
        "CMK-RULE": "ruleset",
    }
    if case.path not in "/domain-types/time_period/collections/all":
        for ticket_id in invalid_link_issues:
            fix_response(
                case,
                response,
                method="GET",
                path="/domain-types/[^/]+/collections/all",
                status_code=200,
                valid_body=True,
                object_type=invalid_link_issues[ticket_id],
                update_items={
                    "value": {"href": "", "method": "GET", "rel": "", "type": "application/json"}
                },
                ticket_id=ticket_id,
            )
    for method, action in (("POST", "create"), ("PUT", "update")):
        fix_response(
            case,
            response,
            method=method,
            path=f"/domain-types/(contact|host|service)_group_config/actions/bulk-{action}/invoke",
            status_code=200,
            valid_body=True,
            update_items={
                "value": {"href": "", "method": "GET", "rel": "", "type": "application/json"}
            },
            ticket_id="CMK-12326",
        )

    # incomplete error responses: missing "detail" field
    fix_response(
        case,
        response,
        method="GET",
        path="/objects/activation_run/{activation_id}(/actions/wait-for-completion/invoke)?",
        status_code=404,
        body={"title": "Activation .* not found.", "detail": "^$"},
        update_body={"detail": "Not found"},
        ticket_id="CMK-12335",
    )
    fix_response(
        case,
        response,
        method="GET",
        path="/objects/discovery_run/{job_id}",
        status_code=404,
        body={"title": "Background job .* not found.", "detail": "^$"},
        update_body={"detail": "Not found"},
        ticket_id="CMK-12335",
    )

    # invalid status: 500 instead of 400
    fix_response(
        case,
        response,
        method="POST",
        path="/domain-types/agent/actions/(bake_and_sign|sign)/invoke",
        status_code=500,
        stack_trace=".*\nKeyError:.*",
        valid_body=True,
        set_status_code=400,
        update_headers={"Content-Type": "{problem}"},
        set_body={"title": "Bad Request", "status": 400, "detail": "Bad Request"},
        ticket_id="CMK-12261",
    )
    fix_response(
        case,
        response,
        method="PUT",
        path="/objects/aux_tag/{aux_tag_id}",
        status_code=500,
        stack_trace=".*\nKeyError:.*",
        valid_body=True,
        set_status_code=400,
        update_headers={"Content-Type": "{problem}"},
        set_body={"title": "Bad Request", "status": 400, "detail": "Bad Request"},
        ticket_id="CMK-12320",
    )
    fix_response(
        case,
        response,
        method="POST|PUT",
        path="/objects/bi_aggregation/{aggregation_id}",
        status_code=500,
        stack_trace=".*\nKeyError:.*",
        valid_body=True,
        set_status_code=400,
        update_headers={"Content-Type": "{problem}"},
        set_body={"title": "Bad Request", "status": 400, "detail": "Bad Request"},
        ticket_id="CMK-TODO",
    )
    fix_response(
        case,
        response,
        method="POST",
        path="/domain-types/metric/actions/filter/invoke",
        status_code=500,
        body={"detail": "There is no graph template with the id .*"},
        set_status_code=400,
        update_body={"title": "Bad Request", "status": 400},
        ticket_id="CMK-TODO",
    )
    fix_response(
        case,
        response,
        method="PUT|DELETE",
        path="/objects/folder_config/{folder}",
        status_code=500,
        stack_trace=".*\nAttributeError: 'NoneType' object has no attribute 'delete_subfolder'.*",
        set_status_code=400,
        set_body={"title": "Bad Request", "status": 400, "detail": "Invalid folder"},
        ticket_id="CMK-12543",
    )
    fix_response(
        case,
        response,
        method="GET",
        path="/domain-types/ruleset/collections/all",
        status_code=500,
        stack_trace=".*\nre.error: bad escape (end of pattern) at position 2*",
        set_status_code=400,
        set_body={"title": "Bad Request", "status": 400, "detail": "Invalid pattern"},
        ticket_id="CMK-12544",
    )

    # invalid status: 400/500 instead of 404
    fix_response(
        case,
        response,
        method="DELETE",
        path="/objects/host_group_config/{name}",
        status_code=400,
        body={"detail": "Unknown host group:.*"},
        valid_body=True,
        set_status_code=404,
        update_headers={"Content-Type": "{problem}"},
        set_body={"title": "Not found", "status": 404, "detail": "Not Found"},
        ticket_id="CMK-12125",
    )
    fix_response(
        case,
        response,
        method="PUT",
        path="/objects/user_config/{username}",
        status_code=500,
        stack_trace=".*\nKeyError:.*",
        valid_body=True,
        set_status_code=404,
        update_headers={"Content-Type": "{problem}"},
        set_body={"title": "Not found", "status": 404, "detail": "Not Found"},
        ticket_id="CMK-12116",
    )
    fix_response(
        case,
        response,
        method="GET",
        path="/objects/rule/{rule_id}",
        status_code=500,
        body={"title": "Unexpected status code returned: 400"},
        set_status_code=404,
        update_headers={"Content-Type": "{problem}"},
        ticket_id="CMK-11900",
    )
    fix_response(
        case,
        response,
        method="GET",
        path="/domain-types/agent/actions/download_by_hash/invoke",
        status_code=500,
        body={"detail": "Unknown agent configuration"},
        set_status_code=404,
        update_body={"title": "Not found", "status": 404},
        ticket_id="CMK-12321",
    )
    fix_response(
        case,
        response,
        method="GET",
        path="/domain-types/agent/actions/download_by_host/invoke",
        status_code=500,
        body={"detail": "No baked agent for this host available"},
        set_status_code=404,
        update_body={"title": "Not found", "status": 404},
        ticket_id="CMK-12724",
    )
    fix_response(
        case,
        response,
        method="GET",
        path="/objects/agent/{agent_hash}",
        status_code=500,
        body={"detail": "Missing config file for agent .*"},
        set_status_code=404,
        update_body={"title": "Not found", "status": 404},
        ticket_id="CMK-12321",
    )

    # other
    fix_response(
        case,
        response,
        method="POST",
        path="/domain-types/agent/actions/bake/invoke",
        status_code=500,
        body={"detail": "Background Job agent_baking already running"},
        set_status_code=409,
        update_body={"title": "Conflict", "status": 409},
        ticket_id="CMK-12246",
    )
