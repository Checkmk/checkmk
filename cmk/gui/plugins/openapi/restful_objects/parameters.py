#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.fields import HostField

from cmk.fields import List, String

HOST_NAME = {
    "host_name": HostField(
        description="A hostname.",
        should_exist=True,
    )
}

OPTIONAL_HOST_NAME = {
    "host_name": HostField(
        description="A hostname.",
        should_exist=True,
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
        pattern="[a-fA-F0-9]{32}|root",
    )
}

NAME_FIELD = {
    "name": String(
        description="A name used as an identifier. Can be of arbitrary (sensible) length.",
        example="pathname",
        pattern="[a-zA-Z0-9][a-zA-Z0-9_-]+",
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
            "by displaying the object it individually. To update this object the currently "
            "stored ETag needs to be the same as the one sent. The content of the ETag can "
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

SERVICE_DESCRIPTION = {
    "service_description": String(
        description="The service description.",
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
