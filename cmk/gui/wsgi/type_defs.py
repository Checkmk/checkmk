#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import List, Literal, TypedDict, Union

Scope = List[str]
UnixTimeStamp = int  # restrict to positive numbers
Audience = Union[str, List[str]]
TokenType = Union[Literal["access_token"], Literal["refresh_token"]]
RFC7662 = TypedDict(
    'RFC7662',
    {
        'active': bool,
        'scope': str,
        'client_id': str,
        'username': str,
        'token_type': TokenType,
        'exp': UnixTimeStamp,  # expires
        'iat': UnixTimeStamp,  # issued
        'nbf': UnixTimeStamp,  # not before
        'sub': str,  # subject
        'aud': Audience,
        'iss': str,  # issuer
        'jti': str,  # json web token-identifier
    },
    total=False,
)
HostGroup = TypedDict('HostGroup', {
    'alias': str,
})
