#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json

from cmk.gui.plugins.openapi import fields

HOST_NAME = {
    'host_name': fields.HostField(
        description="A hostname.",
        should_exist=True,
    )
}

OPTIONAL_HOST_NAME = {
    'host_name': fields.HostField(
        description="A hostname.",
        should_exist=True,
        required=False,
    )
}

IDENT_FIELD = {
    'ident': fields.String(
        description=("The identifier for this object. "
                     "It's a 128bit uuid represented in hexadecimal (32 characters). "
                     "There are no fixed parts or parts derived from the current hardware "
                     "in this number."),
        example='49167bd012b44719a67956cf3ef7b3dd',
        pattern="[a-fA-F0-9]{32}|root",
    )
}

NAME_FIELD = {
    'name': fields.String(
        description="A name used as an identifier. Can be of arbitrary (sensible) length.",
        example='pathname',
        pattern="[a-zA-Z0-9][a-zA-Z0-9_-]+",
    )
}

ACCEPT_HEADER = {
    'Accept': fields.String(
        description="Media type(s) that is/are acceptable for the response.",
        example='application/json',
    )
}

ETAG_IF_MATCH_HEADER = {
    'If-Match': fields.String(
        required=True,
        description=(
            'The ETag of the object to be modified. This value comes from the ETag HTTP header '
            'whenever the object is displayed. To update this object the currently stored ETag '
            'needs to be the same as the one sent.'),
        pattern='[0-9a-fA-F]{32}',
        example='a20ceacf346041dc',
    ),
}

ETAG_HEADER_PARAM = {
    'ETag': fields.String(
        description=('The HTTP ETag header for this resource. It identifies the '
                     'current state of the object and needs to be sent along in '
                     'the "If-Match" request-header for subsequent modifications.'),
        pattern='[0-9a-fA-F]{32}',
        example='a20ceacf346041dc',
    )
}

CONTENT_TYPE = {
    'Content-Type': fields.String(
        required=True,
        description=("A header specifying which type of content is in the request/response body. "
                     "This is required when sending encoded data in a POST/PUT body."),
        example='application/json',
    )
}

SERVICE_DESCRIPTION = {
    'service_description': fields.String(
        description="The service description.",
        example="Memory",
    )
}

QUERY = fields.Nested(
    fields.ExprSchema,
    description=("An query expression in nested dictionary form. If you want to "
                 "use multiple expressions, nest them with the AND/OR operators. "
                 "The query parameter always has priority if applicable"),
    many=False,
    example=json.dumps({
        'op': 'not',
        'expr': {
            'op': '=',
            'left': 'hosts.name',
            'right': 'example.com'
        }
    }),
    required=False,
)

SITES = fields.List(
    fields.String(),
    description="Restrict the query to this particular site.",
    missing=[],
)
