#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""API for Checkmk.

This is the docstring which will be the description of the API.

# Introduction

This API is documented in **OpenAPI format**. This means there is a formal specification for the
whole API surface. This documentation is generated from this specification.

# Authentication

To use this API you have to create an *Automation User* via WATO. The resulting username and
password have to be sent in the `Authentication` HTTP-Header in the *Bearer* format. Example here:

## Security definitions

<SecurityDefinitions />

# How does it work?

This API follows the [HATEOAS](https://en.wikipedia.org/wiki/HATEOAS) principle. While it can be
used in a traditional way, using the elements that enable HATEOAS make it way more powerful and
flexible.

## Text and payload encoding

As specified by the `Content-Type` of `application/json`, the response payload is serialized with
JSON and encoded in UTF-8. Other formats are possible in principle but currently not supported.

## Links

* Every response comes with a collection of `links`. These links are used to provide the consumer
  of the API with follow-up actions. For example a Folder response can have links to resources for
  editing, deleting, moving the folder. The client doesn't have to know about the URL structure,
  it just needs to follow the link.
* (TBD) Every `Action` comes with an endpoint which describes all possible parameters to itself.

## Response format

* Every response is well-formed according to the
  [Restful-Objects standard](https://en.wikipedia.org/wiki/Restful_Objects) and can be treated in
  the same way.
* There are a limited number key concepts in the standard (e.g. object, action, collection, etc.)
  which enables the use of this API without having to understand the details of the implementation
  of each endpoint.

# Client compatibility issues

## Overriding Request Methods

If you have a client which can't do the HTTP PUT or DELETE methods, then you can use the
`X-HTTP-Method-Override` HTTP Header to force the server into believing the client actually sent
such a method. In these cases the HTTP method to use has to be POST. You can't override from GET.

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

DEFAULT_HEADERS = [
    ('Accept', 'Media type(s) that is/are acceptable for the response.', 'application/json'),
]

ETAG_IF_MATCH_HEADER = {
    'in': 'header',
    'name': 'If-Match',
    'required': True,
    'description': 'The ETag of the object to be modified.',
    'schema': {
        'type': 'string'
    },
}

ETAG_HEADER_PARAM = {
    'ETag': {
        'schema': {
            'type': 'string',
            'pattern': '[0-9a-fA-F]{32}',
        },
        'description': ('The HTTP ETag header for this resource. It identifies the '
                        'current state of the object and needs to be sent along in '
                        'the "If-Match" request-header for subsequent modifications.')
    }
}

OPTIONS = {
    'info': {
        'description': apispec.utils.dedent(__doc__).strip(),
        'license': {
            'name': 'GNU General Public License version 2',
            'url': 'https://checkmk.com/gpl.html',
        },
        'contact': {
            'name': 'Contact the Checkmk Team',
            'url': 'https://checkmk.com/contact.php',
            'email': 'feedback@checkmk.com'
        },
    },
    'externalDocs': {
        'description': 'The Checkmk Handbook',
        'url': 'https://checkmk.com/cms.html',
    },
    'x-logo': {
        'url': 'https://checkmk.com/bilder/brand-assets/checkmk_logo_main.png',
        'altText': 'Checkmk',
    },
    'x-tagGroups': [
        {
            'name': 'Endpoints',
            'tags': []
        },
        {
            'name': 'Response Schemas',
            'tags': []
        },
        {
            'name': 'Request Schemas',
            'tags': []
        },
    ],
    'x-ignoredHeaderParameters': [
        'User-Agent',
        'X-Test-Header',
    ],
    'security': [{
        'BearerAuth': []
    }]
}

SPEC = apispec.APISpec("Checkmk REST API",
                       "1.0.0",
                       apispec.utils.OpenAPIVersion("3.0.2"),
                       plugins=[
                           plugins.ValueTypedDictMarshmallowPlugin(),
                           apispec_oneofschema.MarshmallowPlugin(),
                       ],
                       **OPTIONS)
SPEC.components.security_scheme(
    'BearerAuth',
    {
        'type': 'http',
        'scheme': 'bearer',
        'in': 'header',
        'description': 'The format of the header-value is "Bearer $automation_user '
                       '$automation_user_password"\n\nExample: `Bearer hansdampf miezekatze123`',
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
    'Accept', 'header', {
        'description': "Media type(s) that is/are acceptable for the response.",
        'example': 'application/json',
        'schema': {
            'type': 'string',
        }
    })

SPEC.components.parameter(
    'ident', 'path', {
        'description': ("The identifier for this object. "
                        "It's a 128bit uuid represented in hexadecimal (32 characters). "
                        "There are no fixed parts or parts derived from the current hardware "
                        "in this number."),
        'example': '49167bd012b44719a67956cf3ef7b3dd',
        'schema': {
            'pattern': "[a-fA-F0-9]{32}",
            'type': 'string',
        }
    })

SPEC.components.parameter(
    'hostname', 'path', {
        'description': "A hostname.",
        'example': 'example.com',
        'schema': {
            'pattern': "[a-zA-Z0-9-.]+",
            'type': 'string',
        }
    })

SPEC.components.parameter(
    'name', 'path', {
        'description': "A name used as an identifier. Can be of arbitrary (sensible) length.",
        'example': 'pathname',
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
