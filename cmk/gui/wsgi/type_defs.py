#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Iterable
from typing import Literal, TypedDict

from cmk.utils.type_defs import UserId

from cmk.gui.type_defs import AuthType

Scope = list[str]
UnixTimeStamp = int  # restrict to positive numbers
Audience = str | list[str]
TokenType = Literal["access_token", "refresh_token"]


class RFC7662(TypedDict, total=False):
    active: bool
    scope: AuthType
    client_id: str
    username: str
    token_type: TokenType
    exp: UnixTimeStamp  # expires
    iat: UnixTimeStamp  # issued
    nbf: UnixTimeStamp  # not before
    sub: UserId  # subject
    aud: Audience
    iss: str  # issuer
    jti: str  # json web token-identifier


class HostGroup(TypedDict):
    alias: str


WSGIResponse = Iterable[bytes]
