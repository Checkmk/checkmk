#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.regex import GROUP_NAME_PATTERN, REGEX_ID

from cmk.gui.fields import FolderField, HostField
from cmk.gui.watolib.timeperiods import TIMEPERIOD_ID_PATTERN

from cmk.fields import String

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
        example="~",
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

ACCEPT_HEADER = {
    "Accept": String(
        description="Media type(s) that is/are acceptable for the response.",
        example="application/json",
    )
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
