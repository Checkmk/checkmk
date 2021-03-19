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

The API documentation created with this specification is displayed to you with ReDoc (a
responsive Web design for an OpenAPI document) or with Swagger UI (an OpenAPI document
visualization for direct interaction with the API's resources).


# Prerequisites

* You know Checkmk and its principles of setup and configuration.
* You are experienced in using an API, preferably a REST-API.
* You are familiar with at least one of the applications for which sample code is available.
* It helps if you have already worked with ReDoc and/or Swagger UI.


# Responses

As specified by the `Content-Type` of `application/json`, the response payload is serialized with
JSON and encoded in UTF-8.

# Link relations

Every response comes with a collection of `links` to inform the API client on possible
follow-up actions. For example, a folder response can have links to resources for updating,
deleting and moving the folder. The client does not have to know about the URL structure, it
just needs to follow the link. In this sense, the API is quasi self-documenting.
This provision of additional information as a REST-API principle is also called
[HATEOAS](https://en.wikipedia.org/wiki/HATEOAS). In this context,
a `rel` specifies the type of relationship of the concerning resource to the resource that generated
this representation. The rel attribute is only of informational nature for the client.

Objects may have these possible generic link relations:

 * self - The API location of the current object
 * help - Documentation for the currently requested endpoint
 * collection - The API location for a list of object of the current objects' type
 * edit - The API location to update the current object
 * edit-form - The GUI location to edit the current object
 * delete - The API location to delete the current object

Members of collections have also:

 * item - The API location of a member of the current collection

Please note that these (except for self) are completely optional and may or may not be available on
certain endpoints. More specialized link relations are also available:

 * invoke - The API location to invoke an action
 * start - The API location to start a long running process, which the current object represents
 * cancel - The API location to abort the long running process, which the current object represents
 * download - The URL to download the object described by the current endpoint
 * move - The API location to move the current object to another destination

Endpoint specific link relations are also possible.

# Authentication

To use this API from an automated client, a user needs to be set up in Checkmk. Ideally this
would be an *automation* user, with which actions can be performed via the API. For a newly
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
from typing import List, Literal, Dict, TypedDict

import apispec.utils  # type: ignore[import]
import apispec.ext.marshmallow as marshmallow  # type: ignore[import]
import apispec_oneofschema  # type: ignore[import]

from cmk.gui.plugins.openapi import plugins
from cmk.gui.plugins.openapi.restful_objects.parameters import (
    ACCEPT_HEADER,)

from cmk.gui.plugins.openapi.restful_objects.params import to_openapi

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
