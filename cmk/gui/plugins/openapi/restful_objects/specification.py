#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
# Introduction

With the Checkmk REST-API you can transfer and execute the tasks you normally perform
manually in Checkmk's GUI to the Checkmk server via command or script.

REST stands for REpresentational State Transfer and describes an architecture for the exchange of
data on distributed systems - especially for Web services. The implementation of this REST-API is
done via the HTTP/1.1 protocol, where resources are addressed via URIs and accessed with HTTP
methods (GET, POST, PUT, DELETE).

The API is documented in a machine-readable schema and a human-readable format in English, with all
resources, their input and output parameters and the associated value ranges. The API is created
with the OpenAPI specification 3.x, an API description format especially for REST APIs.

The API documentation created with this specification is displayed to you with ReDoc, a responsive
Web design for OpenAPI documents.


# Prerequisites

* You are experienced in using an API, preferably a REST-API.
* You are familiar with at least one of the applications for which sample code is available.
* You know Checkmk and its principles of setup and configuration.


# Using the API documentation

The API documentation's Web design provides 3 panes.

The left navigation pane is used for orientation, search and quick jump to the exact description of
the entries in the middle content pane. The table of contents contains one entry for each API endpoint.
An endpoint uses a URL to refer to the resource that the API provides (e.g., to collect hosts),
along with the method used to access the resource (e.g., GET to display a host).
The endpoints are organized in several folders.

The middle content pane contains all information about the definition of a request (with parameters,
value ranges, default values and descriptions) and the corresponding answers (also with all details).
The possible answers are displayed in different colors, depending on whether the returned HTTP status
code signals success or an error.

The right example pane shows the method and URL for the endpoint selected in the content pane,
followed by several examples of requests: the payload in JSON format (if relevant to the endpoint) and
code examples, such as cURL, HTTPie, Python Requests, or Python Urllib. Then follow the responses
according to the HTTP status. All code examples can be copied to the clipboard with the Copy button.


# Responses

As specified by the `Content-Type` of `application/json`, the response payload is serialized with
JSON and encoded in UTF-8.

All responses are well-formed according to the
[Restful-Objects standard](https://en.wikipedia.org/wiki/Restful_Objects).
There are a limited number of key concepts in the standard (e.g. object, action, collection, etc.)
which enables the use of this API without having to understand the details of the implementation of
each endpoint.

Every response comes with a collection of `links` to inform the API client on possible
follow-up actions. For example, a folder response can have links to resources for updating,
deleting and moving the folder. The client does not have to know about the URL structure, it
just needs to follow the link. In this sense, the API is quasi self-documenting.
This provision of additional information as a REST-API principle is also called
[HATEOAS](https://en.wikipedia.org/wiki/HATEOAS).


# Authentication

To use this API from a automated client, a user needs to be set up in Checkmk. Ideally this
would be an automation-user, with which actions can be performed via the API. For a newly
created site an automation user is already created. You can find it, like other users, in
Checkmk at *Setup* > *Users*.

As an alternative, users who already logged into Checkmk can also access the API, although these
users are not very suitable for automation, because their session will time out eventually.

For scripting, please use the Bearer authentication format.

<SecurityDefinitions />


# Client compatibility issues

## Overriding request methods

If you have a client which cannot do the HTTP PUT or DELETE methods, you can use the
`X-HTTP-Method-Override` HTTP header to force the server into believing the client actually sent
such a method. In these cases the HTTP method to use has to be POST. You cannot override from GET.

## Backwards compatibility

Future versions of this API may add additional fields in the responses. Clients must be written
in a way to NOT expect the absence of a field, as we don't guarantee that.
For backwards compatibility reasons we only keep the fields that have already been there in older
versions. You can consult the documentation to see what changed in each API revision.

"""
from typing import List, Literal, Sequence, Dict, TypedDict, Union

import apispec.utils  # type: ignore[import]
import apispec.ext.marshmallow as marshmallow  # type: ignore[import]
import apispec_oneofschema  # type: ignore[import]

from cmk.gui.plugins.openapi import plugins
from cmk.gui.plugins.openapi.restful_objects.parameters import (
    ACCEPT_HEADER,)

from cmk.gui.plugins.openapi.restful_objects.params import to_openapi
from cmk.gui.plugins.openapi.restful_objects.type_defs import OpenAPIParameter

SECURITY_SCHEMES = {
    'bearerAuth': {
        'type': 'http',
        'scheme': 'bearer',
        'in': 'header',
        'description': 'Use automation user credentials. The format of the header value is '
                       '`Bearer $user $password`. This method has the highest precedence. If it '
                       'succeeds, all other authentication methods are skipped.',
        'bearerFormat': 'username password',
    },
    'webserverAuth': {
        'type': 'http',
        'scheme': 'basic',
        'in': 'header',
        'description': "Use the authentication method of the webserver ('basic' or 'digest'). To "
                       "use this, you'll have to re-configure the site's Apache instance "
                       "yourself. This method takes precedence over the cookieAuth method."
    }
}

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
    ],
    'x-ignoredHeaderParameters': [
        'User-Agent',
        'X-Test-Header',
    ],
    'security': [{
        sec_scheme_name: []
    } for sec_scheme_name in SECURITY_SCHEMES]
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
for sec_scheme_name, sec_scheme_spec in SECURITY_SCHEMES.items():
    SPEC.components.security_scheme(sec_scheme_name, sec_scheme_spec)

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
    params: Sequence[Union[OpenAPIParameter, str]],
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
