#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Dict, Any

from typing_extensions import Literal

# We don't differentiate between raw and cee versions here. It's a unified list of types.
DomainType = Literal[
    'agent',
    'activation_run',
    'contact_group',
    'folder',
    'host',
    'host_group',
    'service_group',
    'user',
]  # yapf: disable

DomainObject = Dict[str, Any]

EndpointName = Literal[
    'cmk/bake',
    'cmk/cancel',
    'cmk/create',
    'cmk/download',
    'cmk/list',
    'cmk/move',
    'cmk/show',
    'cmk/sign',
    'cmk/start',
    'cmk/wait-for-completion',
    'cmk/baking-status',
    'cmk/bakery-status',
]  # yapf: disable

RestfulEndpointName = Literal[
    "describedby",  # sic
    "help",
    "icon",
    "previous",
    "next",
    "self",
    "up",
    ".../action",
    ".../action-param",
    ".../add-to",  # takes params
    ".../attachment",  # takes params
    ".../choice",  # takes params
    ".../clear",
    ".../collection",
    ".../default",
    ".../delete",
    ".../details",  # takes params
    ".../domain-type",
    ".../domain-types",
    ".../element",
    ".../element-type",
    ".../invoke",
    ".../modify",
    ".../persist",
    ".../property",
    ".../remove-from",  # takes params
    ".../return-type",
    ".../services",
    ".../service",  # takes params
    ".../update",
    ".../user",
    ".../value",  # takes params
    ".../version",
]  # yapf: disable

HTTPMethod = Literal["GET", "PUT", "POST", "DELETE"]

PropertyFormat = Literal[
    # String values
    'string',
    # The value should simply be interpreted as a string. This is also the default if
    # the "format" json-property is omitted (or if no domain metadata is available)
    'date-time',  # A date in ISO 8601 format of YYYY-MM-DDThh:mm:ssZ in UTC time
    'date',  # A date in the format of YYYY-MM-DD.
    'time',  # A time in the format of hh:mm:ss.
    'utc-millisec',  # The difference, measured in milliseconds, between the
    # specified time and midnight, 00:00 of January 1, 1970 UTC.
    'big-integer(n)',  # The value should be parsed as an integer, scale n.
    'big-integer(s,p)',  # The value should be parsed as a big decimal, scale n,
    # precision p.
    'blob',  # base-64 encoded byte-sequence
    'clob',  # character large object: the string is a large array of
    # characters, for example an HTML resource
    # Non-string values
    'decimal',  # the number should be interpreted as a float-point decimal.
    'int',  # the number should be interpreted as an integer.
]
