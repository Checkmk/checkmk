#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

from cmk.gui.openapi.framework.model import api_field, api_model


@api_model
class IdentifySessionResponse:
    user_id: str = api_field(description="The user the session belongs to.", example="cmkadmin")


@api_model
class DelegateSessionResponse:
    """The RFC 8693 token exchange response, plus the user the token acts for"""

    access_token: str = api_field(
        description="The access token. Never log or store it.",
        example="cmko1.q2V9...",
    )
    issued_token_type: Literal["urn:ietf:params:oauth:token-type:access_token"] = api_field(
        description="The kind of token issued, in RFC 8693 terms.",
        example="urn:ietf:params:oauth:token-type:access_token",
    )
    token_type: Literal["Bearer"] = api_field(
        description="How to present the token.", example="Bearer"
    )
    expires_in: int = api_field(description="Seconds until the token expires.", example=3600)
    scope: str = api_field(description="What the token may do.", example="read")
    user_id: str = api_field(description="The user the token acts for.", example="cmkadmin")
