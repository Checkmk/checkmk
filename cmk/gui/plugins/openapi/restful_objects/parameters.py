#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.plugins.openapi.restful_objects.utils import ParamDict

HOSTNAME_REGEXP = '[-0-9a-zA-Z_.]+'
HOSTNAME = ParamDict.create(
    'hostname',
    'path',
    description="A hostname.",
    example='example.com',
    schema_pattern=HOSTNAME_REGEXP,
)

IDENT = ParamDict.create(
    'ident',
    'path',
    description=("The identifier for this object. "
                 "It's a 128bit uuid represented in hexadecimal (32 characters). "
                 "There are no fixed parts or parts derived from the current hardware "
                 "in this number."),
    example='49167bd012b44719a67956cf3ef7b3dd',
    schema_pattern="[a-fA-F0-9]{32}|root",
)

NAME = ParamDict.create(
    'name',
    'path',
    description="A name used as an identifier. Can be of arbitrary (sensible) length.",
    example='pathname',
    schema_pattern="[a-zA-Z][a-zA-Z0-9_-]+",
)

ACCEPT_HEADER = ParamDict.create(
    'Accept',
    'header',
    description="Media type(s) that is/are acceptable for the response.",
    example='application/json',
)

ETAG_IF_MATCH_HEADER = ParamDict.create(
    'If-Match',
    'header',
    required=True,
    description=(
        'The ETag of the object to be modified. This value comes from the ETag HTTP header '
        'whenever the object is displayed. To update this object the currently stored ETag '
        'needs to be the same as the one sent.'),
    example='a20ceacf346041dc',
)

ETAG_HEADER_PARAM = ParamDict.create(
    'ETag',
    'header',
    description=('The HTTP ETag header for this resource. It identifies the '
                 'current state of the object and needs to be sent along in '
                 'the "If-Match" request-header for subsequent modifications.'),
    schema_pattern='[0-9a-fA-F]{32}',
    example='a20ceacf346041dc',
)
