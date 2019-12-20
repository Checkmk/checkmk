#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2019             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.
from typing import List, Union, Literal, TypedDict

Scope = List[str]
UnixTimeStamp = int  # restrict to positive numbers
TokenType = Union[Literal["access_token"], Literal["refresh_token"]]
Audience = Union[str, List[str]]
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
