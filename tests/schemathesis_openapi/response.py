#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
import logging
from json.decoder import JSONDecodeError
from re import DOTALL, match
from typing import Any

import requests
import schemathesis
import schemathesis.transports.responses
from requests.structures import CaseInsensitiveDict

from tests.schemathesis_openapi import settings

logger = logging.getLogger(__name__)


DEFAULT_CONTENT_TYPE = "application/json"
PROBLEM_CONTENT_TYPE = "application/problem+json"


def fix_response(
    case: schemathesis.models.Case,
    response: schemathesis.transports.responses.GenericResponse,
    method: str | None = None,
    path: str | None = None,
    body: dict[str, Any] | None = None,
    status_code: int | None = None,
    object_type: str | None = None,
    traceback: str | None = None,
    valid_body: bool | None = None,
    empty_content_type: bool | None = None,
    valid_content_type: bool | None = None,
    set_status_code: int | None = None,
    update_headers: CaseInsensitiveDict | None = None,
    set_body: dict[str, Any] | None = None,
    update_body: dict[str, Any] | None = None,
    update_items: dict[str, Any] | None = None,
    ticket_id: str | None = None,
) -> None:
    """Fix a broken response to suppress a known issue."""
    schema = case.operation.schema

    if case.path.count("/") >= 2:
        response_object_type = case.path.split("/")[2]
    else:
        response_object_type = case.path.replace("/", "")
    raw_schema = schema.raw_schema
    response_content_type = response.headers.get("Content-Type")
    content_types = (
        raw_schema["paths"][case.path][case.method.lower()]["responses"]
        .get(str(response.status_code), {})
        .get("content")
    )
    if content_types is None:
        content_types = (
            raw_schema["paths"][case.path][case.method.lower()]["responses"]
            .get(f"{str(response.status_code)[0]}XX", {})
            .get("content")
        )
    response_content_type_empty = response_content_type is None
    response_content_type_valid = (content_types is None) or (
        response_content_type is not None and response_content_type in content_types
    )
    if response.status_code >= 400:
        auto_content_type = PROBLEM_CONTENT_TYPE
    else:
        auto_content_type = DEFAULT_CONTENT_TYPE
    if content_types and auto_content_type not in content_types:
        auto_content_type = list(content_types.keys())[0]

    try:
        response_content = (
            response._content.decode() if isinstance(response._content, bytes) else "{}"
        )
        response_json = json.loads(response_content)
        response_content_valid = True
    except (UnicodeDecodeError, JSONDecodeError):
        response_content = "{}"
        response_json = {}
        response_content_valid = False
    response_content_expected = response.status_code not in (204, 302)
    if response_content_expected and not response_content_valid:
        if response.status_code == 404:
            # warn only since this is most likely caused by the webserver instead of the API
            logger.warning(
                '%s %s: Response was not in JSON format for status code "%s"!',
                case.method,
                case.path,
                response.status_code,
            )
        else:
            logger.error(
                '%s %s: Response was not in JSON format for status code "%s"!',
                case.method,
                case.path,
                response.status_code,
            )
    elif response_content_valid and not response_content_expected:
        logger.error(
            '%s %s: Unexpected JSON response returned for status code "%s"!',
            case.method,
            case.path,
            response.status_code,
        )

    ext_response = response_json.get("ext", {})
    traceback_key = "stack_trace" if "stack_trace" in ext_response else "exc_traceback"
    response_traceback = "\n".join(ext_response.get(traceback_key, []))

    if (
        (ticket_id is None or ticket_id in settings.suppressed_issues)
        and (method is None or match(method, case.method))
        and (path is None or match(path, case.path))
        and (
            body is None
            or response_json == body
            or all(body.get(_) == response_json.get(_) for _ in body)
            or all(match(body.get(_, ""), response_json.get(_, "")) for _ in body)
        )
        and (
            status_code is None
            or (status_code >= 0 and response.status_code == status_code)
            or (status_code < 0 and -response.status_code != status_code)
        )
        and (object_type is None or match(object_type, response_object_type))
        and (traceback is None or match(traceback, response_traceback, flags=DOTALL))
        and (valid_body is None or response_content_valid == valid_body)
        and (empty_content_type is None or response_content_type_empty == empty_content_type)
        and (valid_content_type is None or response_content_type_valid == valid_content_type)
    ):
        reason = response.reason if isinstance(response, requests.Response) else "n/a"
        if set_status_code:
            logger.warning(
                "%s %s: Suppressed invalid status code, using %s instead of %s (reason=%s)! #%s",
                case.method,
                case.path,
                set_status_code,
                response.status_code,
                reason,
                ticket_id,
            )
            response.status_code = set_status_code
        if update_headers:
            for header, expected_header_value in update_headers.items():
                current_header_value = response.headers.get(header)
                if expected_header_value is None:
                    del response.headers[header]
                else:
                    expected_header_value = expected_header_value.format(
                        auto=auto_content_type, problem=PROBLEM_CONTENT_TYPE
                    )
                    response.headers[header] = expected_header_value
                if current_header_value != expected_header_value:
                    logger.warning(
                        (
                            '%s %s: Suppressed invalid response header "%s" (got "%s"; '
                            'expected "%s") on status code %s (reason=%s)! #%s'
                        ),
                        case.method,
                        case.path,
                        header,
                        current_header_value,
                        expected_header_value,
                        response.status_code,
                        reason,
                        ticket_id,
                    )

        if set_body or update_body or update_items:
            # NOTE: Assigning to response.json will not work,
            # you need to redefine response._content instead!
            if set_body:
                response_json = set_body
            if update_body:
                response_json.update(update_body)
            if update_items:
                for update_key in [
                    _ for _ in update_items if _ in response_json and response_json[_]
                ]:
                    for idx in range(len(response_json[update_key])):
                        response_json[update_key][idx].update(update_items[update_key])
            response._content = json.dumps(response_json).encode()
            logger.warning(
                "%s %s: Suppressed invalid response content on status code %s (%s)! #%s",
                case.method,
                case.path,
                response.status_code,
                reason,
                ticket_id,
            )
