#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.plugins.openapi.restful_objects.utils import ParamDict

HOSTNAME_REGEXP = '[-0-9a-zA-Z_.]+'
HOSTNAME = ParamDict(
    name='hostname',
    location='path',
    description="A hostname.",
    example='example.com',
    schema={
        'pattern': HOSTNAME_REGEXP,
        'type': 'string',
    },
)

IDENT = ParamDict(
    name='ident',
    location='path',
    description=("The identifier for this object. "
                 "It's a 128bit uuid represented in hexadecimal (32 characters). "
                 "There are no fixed parts or parts derived from the current hardware "
                 "in this number."),
    example='49167bd012b44719a67956cf3ef7b3dd',
    schema={
        'pattern': "[a-fA-F0-9]{32}|root",
        'type': 'string',
    },
)

NAME = ParamDict(
    name='name',
    location='path',
    description="A name used as an identifier. Can be of arbitrary (sensible) length.",
    example='pathname',
    schema={
        'pattern': "[a-zA-Z][a-zA-Z0-9_-]+",
        'type': 'string',
    },
)

ACCEPT_HEADER = ParamDict(
    name='Accept',
    location='header',
    description="Media type(s) that is/are acceptable for the response.",
    example='application/json',
    schema={
        'type': 'string',
    },
)
