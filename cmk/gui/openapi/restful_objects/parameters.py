#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.regex import GROUP_NAME_PATTERN, REGEX_ID

from cmk.gui.fields import FolderField, HostField
from cmk.gui.watolib.timeperiods import TIMEPERIOD_ID_PATTERN

from cmk.fields import List, String

HOST_NAME = {
    "host_name": HostField(
        description="A host name.",
        should_exist=True,
    )
}

OPTIONAL_HOST_NAME = {
    "host_name": HostField(
        description="A host name.",
        should_exist=True,
        required=False,
    )
}

OPTIONAL_FOLDER_NAME = {
    "folder_name": FolderField(
        description="A folder name.",
        metadata={"should_exist": True},
        required=False,
    )
}

IDENT_FIELD = {
    "ident": String(
        description=(
            "The identifier for this object. "
            "It's a 128bit uuid represented in hexadecimal (32 characters). "
            "There are no fixed parts or parts derived from the current hardware "
            "in this number."
        ),
        example="49167bd012b44719a67956cf3ef7b3dd",
        pattern="^[a-fA-F0-9]{32}$|root",
    )
}

TIMEPERIOD_NAME_FIELD = {
    "name": String(
        description="A name used as an identifier. Can be of arbitrary (sensible) length.",
        example="pathname",
        pattern=TIMEPERIOD_ID_PATTERN,
    )
}


GROUP_NAME_FIELD = {
    "name": String(
        description="The identifier name of the group.",
        example="pathname",
        pattern=GROUP_NAME_PATTERN,
    )
}

NAME_ID_FIELD = {
    "name": String(
        description="A name used as an identifier. Can be of arbitrary (sensible) length.",
        example="pathname",
        pattern=REGEX_ID,
    )
}

NAME_FIELD = {
    "name": String(
        description="A name used as an identifier. Can be of arbitrary (sensible) length.",
        example="pathname",
        pattern="[a-zA-Z0-9][a-zA-Z0-9_-]*",
    )
}

ACCEPT_HEADER = {
    "Accept": String(
        description="Media type(s) that is/are acceptable for the response.",
        example="application/json",
    )
}

ETAG_IF_MATCH_HEADER = {
    "If-Match": String(
        required=True,
        description=(
            "The value of the, to be modified, object's ETag header. You can get this value "
            "by displaying the object it individually. When ETag validation is enabled in the "
            "REST API, update operations require that the ETag value you provide matches the "
            "object's current server-side ETag. The content of the ETag can "
            "potentially be anything and should be treated as semantically opaque."
        ),
        example='"a20ceacf346041dc"',
    ),
}

ETAG_HEADER_PARAM = {
    "ETag": String(
        description=(
            "The HTTP ETag header for this resource. It identifies the "
            "current state of the object and needs to be sent along in "
            'the "If-Match" request-header for subsequent modifications. '
            "Please note that the actual ETag returned by some endpoints "
            "may look different than the one shown in this example."
        ),
        example='"a20ceacf346041dc"',
    )
}

CONTENT_TYPE = {
    "Content-Type": String(
        required=True,
        description=(
            "A header specifying which type of content is in the request/response body. "
            "This is required when sending encoded data in a POST/PUT body. When the "
            "request body is empty, this header should not be sent."
        ),
        example="application/json",
    )
}

HEADER_CHECKMK_EDITION = {
    "X-Checkmk-Edition": String(
        required=True,
        description=("The checkmk edition."),
        example="cre",
    ),
}

HEADER_CHECKMK_VERSION = {
    "X-Checkmk-Version": String(
        required=True,
        description=("The checkmk version."),
        example="2.2.0p10",
    ),
}

SERVICE_DESCRIPTION = {
    "service_description": String(
        description="The service name.",
        example="Memory",
    )
}

SITES = List(
    String(),
    description="Restrict the query to this particular site.",
    load_default=[],
)

USERNAME = {
    "username": String(
        description="A username.",
        example="user",
    )
}
