#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated

from annotated_types import MaxLen
from pydantic import StringConstraints

from cmk.gui.openapi.framework.model import api_field, api_model, ApiOmitted

_CookieValue = Annotated[str, StringConstraints(min_length=1, max_length=1024)]

_PermissionName = Annotated[str, StringConstraints(min_length=1, max_length=256)]


@api_model
class IdentifySessionRequest:
    session_cookie: _CookieValue = api_field(
        description="The value of the auth_<site> cookie the browser sent.",
        example="cmkadmin:4f1c2b1e-0d7a-4a3b-9a55-8d9d7c3a2b10:9c1e...",
    )
    required_permissions: Annotated[list[_PermissionName], MaxLen(50)] | ApiOmitted = api_field(
        default_factory=ApiOmitted,
        description=(
            "Permissions to look up for the user of the session. The answer says for each one "
            "whether the user holds it. The endpoint does not refuse a request because a "
            "permission is missing, the caller decides what to do with the answer. A name that "
            "is not a registered permission is reported as not held."
        ),
        example=["general.use"],
    )


@api_model
class DelegateSessionRequest:
    session_cookie: _CookieValue = api_field(
        description="The value of the auth_<site> cookie the browser sent.",
        example="cmkadmin:4f1c2b1e-0d7a-4a3b-9a55-8d9d7c3a2b10:9c1e...",
    )
    resource: Annotated[str, StringConstraints(min_length=1, max_length=2048)] = api_field(
        description="The URI of the service the token is for, for example the MCP server.",
        example="https://monitoring.example.com/mysite/check_mk/mcp",
    )
    scope: str = api_field(
        description='What the token may do: "read", "write" or "read write". Write includes read.',
        example="read",
    )
