#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
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

## Backwards compatibility

Future versions of this API may add additional fields in the responses. Clients must be written
in a way to NOT expect the absence of a field, as we don't guarantee that.
For backwards compatibility reasons we only keep the fields that have already been there in older
versions. You can consult the documentation to see what changed in each API revision.

"""
from typing import List, Literal, Sequence, Dict, TypedDict

import apispec.utils  # type: ignore[import]
import apispec.ext.marshmallow as marshmallow  # type: ignore[import]
import apispec_oneofschema  # type: ignore[import]

from cmk.gui.plugins.openapi import plugins
from cmk.gui.plugins.openapi.restful_objects.parameters import (
    ACCEPT_HEADER,)

from cmk.gui.plugins.openapi.restful_objects.params import to_openapi
from cmk.gui.plugins.openapi.restful_objects.type_defs import OpenAPIParameter

DEFAULT_HEADERS = [
    ('Accept', 'Media type(s) that is/are acceptable for the response.', 'application/json'),
]

OpenAPIInfoDict = TypedDict(
    'OpenAPIInfoDict',
    {
        'description': str,
        'license': Dict[str, str],
        'contact': Dict[str, str],
    },
    total=True,
)

TagGroup = TypedDict(
    'TagGroup',
    {
        'name': str,
        'tags': List[str],
    },
    total=True,
)

ReDocSpec = TypedDict(
    "ReDocSpec",
    {
        'info': OpenAPIInfoDict,
        'externalDocs': Dict[str, str],
        'security': List[Dict[str, List[str]]],
        'x-logo': Dict[str, str],
        'x-tagGroups': List[TagGroup],
        'x-ignoredHeaderParameters': List[str],
    },
    total=True,
)

OPTIONS: ReDocSpec = {
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
            'name': 'Monitoring',
            'tags': []
        },
        {
            'name': 'Setup',
            'tags': []
        },
        # TODO: remove
        {
            'name': 'Endpoints',
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

__version__ = "0.3.2"


def make_spec(options: ReDocSpec):
    return apispec.APISpec(
        "Checkmk REST-API",
        __version__,
        apispec.utils.OpenAPIVersion("3.0.2"),
        plugins=[
            marshmallow.MarshmallowPlugin(),
            plugins.ValueTypedDictMarshmallowPlugin(),
            apispec_oneofschema.MarshmallowPlugin(),
        ],
        **options,
    )


SPEC = make_spec(options=OPTIONS)
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
for header_name, field in ACCEPT_HEADER.items():
    SPEC.components.parameter(
        header_name,
        'header',
        to_openapi([{
            header_name: field
        }], 'header')[0],
    )

ErrorType = Literal['ignore', 'raise']


def find_all_parameters(
    params: Sequence[OpenAPIParameter],
    errors: ErrorType = 'ignore',
) -> List[OpenAPIParameter]:
    """Find all parameters, while de-referencing string based parameters.

    Parameters can come in dictionary, or string form. If they are a dictionary they are supposed
    to be completely self-contained and can be specified with the same name multiple times for
    different endpoints even with different values.

    A string parameter is just a reference to a globally defined parameter, which can only be
    defined once with that name.

    This function de-references these string based parameters and emits a list of all parameters
    that it has been given in their dictionary form.

    Examples:

        >>> find_all_parameters([{'name': 'fizz', 'in': 'query'}, 'foobar'])
        [{'name': 'fizz', 'in': 'query'}]

        >>> find_all_parameters(['foobar'])
        []

        >>> find_all_parameters(['foobar'], errors='raise')
        Traceback (most recent call last):
           ...
        ValueError: Param 'foobar', assumed globally defined, was not found.

    Args:
        params:
            Either as a dict or as a string. If it is a string it will be replaced
            by it's globally defined parameter (if found).

        errors:
            What to do when an error is detected. Can be either 'raise' or 'ignore'.

    Returns:
        A list of parameters, all in their dictionary form.

    Raises:
        ValueError: Whenever a parameter could not be de-referenced.

    """
    result = []
    global_params = SPEC.components.to_dict().get('parameters', {})

    for _param in params:
        if isinstance(_param, dict):
            result.append(_param)
        elif isinstance(_param, str):
            if _param in global_params:
                result.append(global_params[_param])
                continue

            if errors == 'raise':
                raise ValueError(f"Param {_param!r}, assumed globally defined, was not found.")
    return result
