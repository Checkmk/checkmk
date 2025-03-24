#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence

from cmk.gui.http import HTTPMethod
from cmk.gui.openapi.restful_objects.type_defs import ETagBehaviour, StatusCodeInt, TagGroup


def endpoint_ident(method: HTTPMethod, route_path: str, content_type: str) -> str:
    """Provide an identity for an endpoint

    This can be used for keys in a dictionary, e.g. the ENDPOINT_REGISTRY."""
    return f"{method}:{route_path}:{content_type}"


def identify_expected_status_codes(
    method: HTTPMethod,
    doc_category: TagGroup,
    content_type: str,
    etag: ETagBehaviour | None,
    has_response: bool,
    has_path_params: bool,
    has_query_params: bool,
    has_request_schema: bool,
    additional_status_codes: Sequence[StatusCodeInt],
) -> set[StatusCodeInt]:
    """Identify which status codes are expected to be returned by an endpoint."""
    expected_status_codes = set(additional_status_codes)
    expected_status_codes.add(406)

    if content_type != "application/json" or (content_type == "application/json" and has_response):
        expected_status_codes.add(200)

    if not has_response:
        expected_status_codes.add(204)

    if doc_category == "Setup":
        expected_status_codes.add(403)

    if method in ("put", "post"):
        expected_status_codes.add(400)  # bad request
        expected_status_codes.add(415)  # unsupported media type

    if has_path_params:
        expected_status_codes.add(404)  # not found

    if has_query_params or has_request_schema:
        expected_status_codes.add(400)  # bad request

    if etag in ("input", "both"):
        expected_status_codes.add(412)  # precondition failed
        expected_status_codes.add(428)  # precondition required

    return expected_status_codes
