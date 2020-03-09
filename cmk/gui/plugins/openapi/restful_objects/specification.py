#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""API for Checkmk.

This is the docstring which will be the description of the API.

"""
import re
import typing

if typing.TYPE_CHECKING:
    pass

import apispec.utils  # type: ignore
import apispec_oneofschema  # type: ignore

from cmk.gui.plugins.openapi import plugins

# Path parameters look like {varname} and need to be checked.
PARAM_RE = re.compile(r"\{([a-z][a-z0-9]*)\}")

ETAG_IF_MATCH_HEADER = {
    'in': 'header',
    'name': 'If-Match',
    'required': True,
    'description': 'The ETag of the object to be modified.',
    'schema': {
        'type': 'string'
    },
}

SPEC = apispec.APISpec(
    title="Checkmk REST API",
    version="1.0.0",  # Implementation version of API
    openapi_version=apispec.utils.OpenAPIVersion("3.0.2"),
    plugins=[
        plugins.ValueTypedDictMarshmallowPlugin(),
        apispec_oneofschema.MarshmallowPlugin(),
    ],
    info={
        'description': apispec.utils.dedent(__doc__).strip(),
        'license': {
            'name': 'GNU General Public License version 2',
            'url': 'https://checkmk.com/gpl.html',
        },
        'contact': {
            'name': 'Contact the Checkmk Team',
            'url': 'https://checkmk.com/contact.php',
            'email': 'feedback@check-mk.org'
        },
    },
    externalDocs={
        'description': 'The Checkmk Handbook',
        'url': 'https://checkmk.com/cms.html',
    },
    security=[{
        'BearerAuth': []
    }],
)

SPEC.components.security_scheme(
    'BearerAuth',
    {
        'type': 'http',
        'scheme': 'bearer',
        'in': 'header',
        'description': 'The format of the header-value is "Bearer $automation_user '
                       '$automation_user_password"',
        'bearerFormat': 'username password',
        'x-bearerInfoFunc': 'cmk.gui.wsgi.auth.bearer_auth',
    },
)

# All the supported response headers by the spec.

# response_headers = {
#     'Allow',
#     'Cache-Control',
#     'Last-Modified',
#     'Warning',
#     'Content-Type',
# }

SPEC.components.parameter(
    'ident', 'path', {
        'description': ("The identifier for this object. "
                        "It's a 128bit uuid represented in hexadecimal (32 characters). "
                        "There are no fixed parts or parts derived from the current hardware "
                        "in this number."),
        'schema': {
            'pattern': "[a-fA-F0-9]{32}",
            'type': 'string',
        }
    })

SPEC.components.parameter('hostname', 'path', {
    'description': "A hostname.",
    'schema': {
        'pattern': "[a-zA-Z0-9-.]+",
        'type': 'string',
    }
})

SPEC.components.parameter('name', 'path', {
    'description': "A name.",
    'schema': {
        'pattern': "[a-zA-Z][a-zA-Z0-9_-]+",
        'type': 'string',
    }
})


def add_operation(path, method, operation_spec):
    """Add an operation spec to the SPEC object.

    """
    # TODO: check if path method combination already there, if not raise exception
    SPEC.path(path=path, operations={method.lower(): operation_spec})
