#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.openapi.restful_objects.type_defs import OpenAPIParameter

ETAG_HEADER: OpenAPIParameter = {
    "name": "ETag",
    "description": (
        "The HTTP ETag header for this resource. It identifies the "
        "current state of the object and needs to be sent along in "
        'the "If-Match" request-header for subsequent modifications. '
        "Please note that the actual ETag returned by some endpoints "
        "may look different than the one shown in this example."
    ),
    "in": "header",
    "schema": {
        "type": "string",
    },
    "example": '"a20ceacf346041dc"',
}

ETAG_IF_MATCH_HEADER: OpenAPIParameter = {
    "name": "If-Match",
    "description": (
        "The value of the, to be modified, object's ETag header. You can get this value "
        "by displaying the object it individually. When ETag validation is enabled in the "
        "REST API, update operations require that the ETag value you provide matches the "
        "object's current server-side ETag. The content of the ETag can "
        "potentially be anything and should be treated as semantically opaque."
    ),
    "in": "header",
    "required": True,
    "schema": {
        "type": "string",
    },
    "example": '"a20ceacf346041dc"',
}

CONTENT_TYPE: OpenAPIParameter = {
    "name": "Content-Type",
    "description": (
        "A header specifying which type of content is in the request/response body. "
        "This is required when sending encoded data in a POST/PUT body. When the "
        "request body is empty, this header should not be sent."
    ),
    "in": "header",
    "required": True,
    "schema": {
        "type": "string",
    },
    "example": "application/json",
}

HEADER_CHECKMK_EDITION: OpenAPIParameter = {
    "name": "X-Checkmk-Edition",
    "description": "The checkmk edition.",
    "in": "header",
    "required": True,
    "schema": {
        "type": "string",
    },
    "example": "cre",
}

HEADER_CHECKMK_VERSION: OpenAPIParameter = {
    "name": "X-Checkmk-Version",
    "description": "The checkmk version.",
    "in": "header",
    "required": True,
    "schema": {
        "type": "string",
    },
    "example": "2.2.0p10",
}
