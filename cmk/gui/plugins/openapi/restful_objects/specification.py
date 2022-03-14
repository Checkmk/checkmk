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

## JSON envelope attributes for objects

All objects are wrapped in a JSON structure called a "Domain Object" which take the following
form:

    {
        "domainType": <domain type>,
        "instanceId": <string to uniquely identify domain object>,
        "title": <human readable header>,
        "links": [<relation link>, ...],
        "extensions": {
            <attribute name>: <attribute value>,
            ...
        },
        "members": {
            <member name>: <member definition>,
            ...
        }
     }

The collections `members`, `extensions` and `links` are defined as such:

 * domainType - The type of object this refers to, e.g. `host`, and `service`.
 * instanceId - The globally unique identifier for this particular object.
 * title - A human readable string which is only relevant for user interfaces.
 * links - A collection of links to other resources or actions.
 * extensions - The data container for all direct attributes of the object.
 * members - The container for external resources, like linked foreign objects or actions.

### Note

Previously, an attribute called `members` has been used in these objects, but it will no longer be
used. All relations to other objects will be listed in the `links` attribute.

## JSON envelope for collections

For collections, the JSON envelope looks slightly different.

    {
        "domainType": <domain type>,
        "instanceId": <string to uniquely identify domain object>,
        "title": <human readable header>,
        "links": [<relation link>, ...],
        "extensions": {
            <attribute name>: <attribute value>,
            ...
        },
        "value": [<domain object 1>, <domain object 2>, ...],
    }

## Link relations

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

# Updating values

When an object is updated by multiple requests at the same time, it can happen that the second
request will overwrite important values from the first request. This is known as the "lost update
problem" and can be prevented by a locking scheme. The scheme that Checkmk uses for this is called
an "optimistic lock" and allows read access even when writes are happening. It works as follows:

1. The user fetches the object to be modified.
2. The server responds with the data and an HTTP `ETag` header containing a value which is something
   like the "checksum" of the object.
3. In order to modify the object, the user sends an update request with an HTTP `If-Match` header
   which contains the value of the previously fetched `ETag`. This ensures that the writer has seen
   the object to be modified. If any modifications by someone else were to happen between the
   request (1) and the update (3) these values would not match and the update would fail.

This scheme is used for most `PUT` requests throughout the REST API and always works the same way.
Detailed documentation of the various involved fields as well as the possible error messages can
be found on the documentation of each affected endpoint.

# Querying Status Data

The endpoints in the category "Monitoring" support arbitrary Livestatus expressions (including And,
Or combinators) and all columns of some specific tables can be queried.

### Note

You can find an introduction to basic monitoring principles including host and service status in the
[Checkmk guide](https://docs.checkmk.com/latest/en/monitoring_basics.html).

## Filter expressions

A *filter expression* is a recursively defined structure containing *binary expression nodes*,
*negation nodes* or *combination nodes*. With *filter expressions*, very complex Livestatus queries
can be constructed.

## Binary expression node

A *binary expression node* represents one condition on which to filter. `left` is always a
Livestatus column name, `right` is always a value.

### Definition

    {'op': <livestatus operator>, 'left': <livestatus column>, 'right': <value>}

### Operators

A list of all list of all possible
[Livestatus filter operators](https://docs.checkmk.com/latest/en/livestatus_references.html#heading_filter),
can be found in the Checkmk documentation.

### Example

This example filters for an entry where the host_name equals to "example.com".

    {'op': '=', 'left': 'host_name', 'right': 'example.com'}

### Note

For the specific table used, please consult the endpoint documentation.

## Negation node

There is only one negation node, the `not` expression, which logically negates a *filter
expression*. `expr` is a valid *filter expression*, so any *binary expression node*, *negation
node* or *combination node* may be used here.

### Definition

     {'op': 'not', 'expr': <any filter expr>}

### Example

This example filters for hosts which **do not** have the host_name "example.com".

    {'op': 'not', 'expr': {'op': '=', 'left': 'host_name', 'right': 'example.com'}}

This is equivalent to

    {'op': '!=', 'left': 'host_name', 'right': 'example.com'}

## Combination nodes

`and` and `or` combinators are supported. They can be nested arbitrarily. `expr` is a list of
valid *filter expressions*, so any number of *binary nodes*, *negation nodes* or *combination nodes*
may be used there. These expression do not have to all be of the same type, so a mix of *binary
expression nodes*, *negation nodes* and *combination nodes* is also possible.

### Definition

This results in a *filter expression* in which all the contained expression must be true:

    {'op': 'and', 'expr': [<any filter expr>, ...]}

This results in a *filter expression* in which only one of the contained expression needs to
be true:

    {'op': 'or', 'expr': [<any filter expr>, ...]}

### Example

This example filters for the host "example.com" only when the `state` column is set to `0`, which
means the state is OK.

    {'op': 'and', 'expr': [{'op': '=', 'left': 'host_name', 'right': 'example.com'},
                            {'op': '=', 'left': 'state', 'right': 0}}

# Table definitions

The following Livestatus tables can be queried through the REST-API. Which table is being used
in a particular endpoint can be seen in the endpoint documentation.

$TABLE_DEFINITIONS

# Authentication

To use this API from an automated client, a user needs to be set up in Checkmk. Any kind of user,
be it *automation* or *GUI* users, can be used to access the REST API. On a newly created site
some users are already created. You can configure them in Checkmk at *Setup* > *Users*.

For the various authentication methods that can be used please consult the following descriptions,
which occur in the order of precedence. This means that on a request which receives multiple
authentication methods, the one with the hightes priority "wins" and is used. This is especially
convenient when developing automation scripts, as these can directly be used with either the
currently logged in GUI user, or the "Bearer" authentication method which takes precedence over the
GUI authentication method. The result is that the user doesn't have to log out to check that the
scripts works with the other method.

<SecurityDefinitions />

# Compatibility

## HTTP client compatibility

If you have a client which cannot do the HTTP PUT or DELETE methods, you can use the
`X-HTTP-Method-Override` HTTP header to force the server into believing the client actually sent
such a method. In these cases the HTTP method to use has to be POST. You cannot override from GET.

## Compatibility policy

It is our policy to keep all documented parts backwards compatible, as long as there is no
compelling reason (like security, etc) to break compatibility.

In the event of a break in backwards compatibility, these changes are documented and, if possible,
announced by deprecating the field or endpoint in question beforehand. Please understand that this
can't be promised for all cases (security, etc) though.

## Versioning

### Definition

The REST API is versioned by a *major* and *minor* version number.

The *major* number is incremented when backwards incompatible changes to the API have been made.
This will reset the *minor* number to *0*. A *werk* which contains the details of the change and
marking the change as incompatible will be released when this happens.

Th *minor* number will be increased when backwards compatible changes are added to the API. A
*werk* detailing the additions will be released when this happens.

**Note:** Despite the noted backward compatibility, API consumers are best to ensure that their
implementation does not disrupt use-case requirements.

### Usage

The *major* version is part of the URL of each endpoint, while the whole version (in the form
*major*.*minor*) can be sent via the HTTP header `X-API-Version`. If the header is not sent,
the most recent *minor* version of the through the URL selected *major* version is used.
The header will also be present in the accompanying HTTP response.

### Format

 * URL: *v1*, *v2*, etc.
 * X-API-Version HTTP header: *major.minor*

### Notes

 * In the first release, the version part in the URL has been documented as `1.0`. These
   URLs will continue to work in the future, although using the `X-API-Version` header will not be
   possible with this version identifier. You have to use the above documented format (v1, v2, ...)
   in the URL to be able to use the `X-API-Version` header.

## Undocumented behaviour

We cannot guarantee bug-for-bug backwards compatibility. If a behaviour of an endpoint is not
documented we may change it without incrementing the API version.

"""
from typing import Dict, List, Literal, TypedDict

import apispec.ext.marshmallow as marshmallow  # type: ignore[import]
import apispec.utils  # type: ignore[import]
import apispec_oneofschema  # type: ignore[import]

from cmk.gui.fields.openapi import CheckmkMarshmallowPlugin
from cmk.gui.plugins.openapi.restful_objects.documentation import table_definitions
from cmk.gui.plugins.openapi.restful_objects.parameters import ACCEPT_HEADER
from cmk.gui.plugins.openapi.restful_objects.params import to_openapi

SECURITY_SCHEMES = {
    "headerAuth": {
        "type": "http",
        "scheme": "bearer",
        "description": "Use user credentials in the `Authorization` HTTP header. "
        "The format of the header value is `$user $password`. This method has the "
        "highest precedence. If it succeeds, all other authentication methods are "
        "skipped.",
        "bearerFormat": "username password",
    },
    "webserverAuth": {
        "type": "http",
        "scheme": "basic",
        "description": "Use the authentication method of the webserver ('basic' or 'digest'). To "
        "use this, you'll either have to re-configure the site's Apache instance "
        "yourself, or disable multi-site logins via `omd config`. This method "
        "takes precedence over the `cookieAuth` method.",
    },
}

DEFAULT_HEADERS = [
    ("Accept", "Media type(s) that is/are acceptable for the response.", "application/json"),
]

OpenAPIInfoDict = TypedDict(
    "OpenAPIInfoDict",
    {
        "description": str,
        "license": Dict[str, str],
        "contact": Dict[str, str],
    },
    total=True,
)

TagGroup = TypedDict(
    "TagGroup",
    {
        "name": str,
        "tags": List[str],
    },
    total=True,
)

ReDocSpec = TypedDict(
    "ReDocSpec",
    {
        "info": OpenAPIInfoDict,
        "externalDocs": Dict[str, str],
        "security": List[Dict[str, List[str]]],
        "x-logo": Dict[str, str],
        "x-tagGroups": List[TagGroup],
        "x-ignoredHeaderParameters": List[str],
    },
    total=True,
)

OPTIONS: ReDocSpec = {
    "info": {
        "description": apispec.utils.dedent(__doc__)
        .strip()
        .replace("$TABLE_DEFINITIONS", "\n".join(table_definitions())),
        "license": {
            "name": "GNU General Public License version 2",
            "url": "https://checkmk.com/gpl.html",
        },
        "contact": {
            "name": "Contact the Checkmk Team",
            "url": "https://checkmk.com/contact.php",
            "email": "feedback@checkmk.com",
        },
    },
    "externalDocs": {
        "description": "User guide",
        "url": "https://docs.checkmk.com/master",
    },
    "x-logo": {
        "url": "https://checkmk.com/bilder/brand-assets/checkmk_logo_main.png",
        "altText": "Checkmk",
    },
    "x-tagGroups": [
        {"name": "Monitoring", "tags": []},
        {"name": "Setup", "tags": []},
        {"name": "Checkmk Internal", "tags": []},
    ],
    "x-ignoredHeaderParameters": [
        "User-Agent",
        "X-Test-Header",
    ],
    "security": [{sec_scheme_name: []} for sec_scheme_name in SECURITY_SCHEMES],
}

__version__ = "1.0"


def make_spec(options: ReDocSpec):
    return apispec.APISpec(
        "Checkmk REST-API",
        __version__,
        apispec.utils.OpenAPIVersion("3.0.2"),
        plugins=[
            marshmallow.MarshmallowPlugin(),
            apispec_oneofschema.MarshmallowPlugin(),
            CheckmkMarshmallowPlugin(),
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
        "header",
        to_openapi([{header_name: field}], "header")[0],
    )

ErrorType = Literal["ignore", "raise"]
