#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


"""
# Introduction

With the Checkmk REST-API you can transfer and execute the tasks you normally perform
manually in Checkmk's GUI to the Checkmk server via command or script.

REST stands for Representational State Transfer and describes an architecture for the exchange of
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
4. If you are sure you are not updating objects simultaneously and want to avoid first fetching the
   object in order to obtain its ETag value, you can bypass this step by providing a "*" for the
   the 'If-Match' header like so.  `"If-Match": "*"`

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
                            {'op': '=', 'left': 'state', 'right': 0}]}

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
authentication methods, the one with the highest priority "wins" and is used. This is especially
convenient when developing automation scripts, as these can directly be used with either the
currently logged in GUI user, or the "Bearer" authentication method which takes precedence over the
GUI authentication method. The result is that the user doesn't have to log out to check that the
scripts works with the other method.

<SecurityDefinitions />



# Queries through the REST API

Given that Livestatus handles commands asynchronously, the Rest API  is only responsible for the
preparation and dispatch of these commands, without confirming their execution. To ensure the
commands sent to Livestatus are executed as intended, users must verify this on their own.

The following script is an example of how to create a host downtime and check that it has indeed been created:


    #!/usr/bin/env python3
    import requests
    import pprint
    import time
    from datetime import datetime, timedelta

    # Checkmk server details
    SERVER = "localhost"
    SITE_NAME = "central"
    USERNAME = "automation"
    PASSWORD = "test123"
    PROTOCOL = "http"
    API_URL = f"{PROTOCOL}://{SERVER}/{SITE_NAME}/check_mk/api/1.0"

    session = requests.Session()
    session.headers["Authorization"] = f"Bearer {USERNAME} {PASSWORD}"
    session.headers["Accept"] = "application/json"

    # Target host and downtime details
    target_host = "host01"
    downtime_start = (datetime.now() + timedelta(hours=1)).replace(microsecond=0).isoformat() + "Z"
    downtime_end = (datetime.now() + timedelta(hours=2)).replace(microsecond=0).isoformat() + "Z"
    comment = "Security updates #1234"

    # Send create downtime command
    resp = session.post(
        f"{API_URL}/domain-types/downtime/collections/host",
        headers={
            "Content-Type": "application/json",
        },
        json={
            "start_time": downtime_start,
            "end_time": downtime_end,
            "comment": comment,
            "downtime_type": "host",
            "host_name": target_host,
        },
    )
    if resp.status_code != 204:
        raise RuntimeError(pprint.pformat(resp.json()))

    # Check if downtime was created. Retry up to 5 times at 5 seconds intervals
    found = False
    for retry in range(5):
        result = session.get(
            f"{API_URL}/domain-types/downtime/collections/all",
            params={
                "host_name": target_host,
                "downtime_type": "host",
                "site_id": SITE_NAME,
                "query": '{"op": "and", "expr": [{"op": "=", "left": "comment", "right": "'
                + comment
                + '"}, {"op": "=", "left": "type", "right": "2"}]}',
            },
        )
        if (result.status_code == 200) and (len(result.json()["value"]) > 0):
            found = True
            break

        time.sleep(5)
        print(f"Retrying ({retry+1}) after 5 seconds...")

    if not found:
        raise RuntimeError("Downtime not found.")

    print("Downtime successfully created.")


# Compatibility

## HTTP client compatibility

If you have a client which cannot do the HTTP PUT or DELETE methods, you can use the
`X-HTTP-Method-Override` HTTP header to force the server into believing the client actually sent
such a method. In these cases the HTTP method to use has to be POST. You cannot override from GET.

## Compatibility policy

It is our policy to keep all documented parts backwards compatible, as long as there is no
compelling reason (like security, etc.) to break compatibility.

In the event of a break in backwards compatibility, these changes are documented and, if possible,
announced by deprecating the field or endpoint in question beforehand. Please understand that this
can't be promised for all cases (security, etc.) though.

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

from typing import Any, get_args, TypedDict

import apispec_oneofschema
import openapi_spec_validator
from apispec import APISpec
from apispec import utils as apispec_utils
from apispec.ext.marshmallow import MarshmallowPlugin

from cmk.ccc import store
from cmk.ccc import version as cmk_version
from cmk.ccc.site import omd_site, SiteId

from cmk.utils.paths import omd_root

from cmk.gui import main_modules
from cmk.gui.openapi.framework.api_config import APIVersion
from cmk.gui.openapi.framework.registry import (
    EndpointDefinition,
)
from cmk.gui.openapi.restful_objects import Endpoint
from cmk.gui.openapi.restful_objects.documentation import table_definitions
from cmk.gui.openapi.restful_objects.parameters import ACCEPT_HEADER
from cmk.gui.openapi.restful_objects.params import marshmallow_to_openapi
from cmk.gui.openapi.restful_objects.type_defs import EndpointTarget, OperationObject
from cmk.gui.openapi.restful_objects.versioned_endpoint_map import (
    discover_endpoints,
)
from cmk.gui.openapi.spec.plugin_marshmallow import CheckmkMarshmallowPlugin
from cmk.gui.openapi.spec.plugin_pydantic import CheckmkPydanticPlugin
from cmk.gui.openapi.spec.spec_generator._doc_marshmallow import marshmallow_doc_endpoints
from cmk.gui.openapi.spec.spec_generator._doc_pydantic import pydantic_endpoint_to_doc_endpoint
from cmk.gui.openapi.spec.spec_generator._type_defs import DocEndpoint
from cmk.gui.openapi.spec.utils import spec_path
from cmk.gui.session import SuperUserContext
from cmk.gui.utils import get_failed_plugins
from cmk.gui.utils.script_helpers import gui_context

Ident = tuple[str, str]


def main(version: APIVersion) -> int:
    main_modules.load_plugins()
    if errors := get_failed_plugins():
        raise Exception(f"The following errors occurred during plug-in loading: {errors}")

    with gui_context(), SuperUserContext():
        for target in get_args(EndpointTarget):
            store.save_object_to_file(
                spec_path(target),
                _generate_spec(version, _make_spec(version), target, omd_site()),
                pprint_value=False,
            )
    return 0


def _generate_spec(
    version: APIVersion, spec: APISpec, target: EndpointTarget, site: SiteId, validate: bool = True
) -> dict[str, Any]:
    undocumented_tag_groups = set("Undocumented Endpoint")

    if cmk_version.edition(omd_root) == cmk_version.Edition.CSE:
        undocumented_tag_groups.add("Checkmk Internal")

    populate_spec(version, spec, target, undocumented_tag_groups, str(omd_site()))
    generated_spec = spec.to_dict()
    _add_cookie_auth(generated_spec, site)
    if not validate:
        return generated_spec

    # TODO: Need to investigate later what is going on here after cleaning up a bit further
    openapi_spec_validator.validate(generated_spec)  # type: ignore[arg-type]
    return generated_spec


def populate_spec(
    api_version: APIVersion,
    spec: APISpec,
    target: EndpointTarget,
    undocumented_tag_groups: set[str],
    site_name: str,
) -> APISpec:
    methods = ["get", "put", "post", "delete"]

    def sort_key(e: DocEndpoint) -> tuple[str | int, ...]:
        return e.doc_sort_index, e.family_name, methods.index(e.method), e.path, e.effective_path

    seen_paths: dict[Ident, OperationObject] = {}
    ident: Ident
    doc_endpoints = []

    marshmallow_endpoints, versioned_endpoints = get_endpoints_for_version(api_version)

    marshmallow_endpoint: Endpoint
    for marshmallow_endpoint in marshmallow_endpoints:
        if (
            target in marshmallow_endpoint.blacklist_in
            or marshmallow_endpoint.tag_group in undocumented_tag_groups
        ):
            continue
        doc_endpoints.extend(
            [
                doc_endpoint
                for doc_endpoint in marshmallow_doc_endpoints(spec, marshmallow_endpoint, site_name)
            ]
        )

    for versioned_endpoint in versioned_endpoints:
        if (
            target in versioned_endpoint.doc.exclude_in_targets
            or versioned_endpoint.doc.group in undocumented_tag_groups
        ):
            continue
        doc_endpoints.append(
            pydantic_endpoint_to_doc_endpoint(spec, versioned_endpoint.spec_endpoint(), site_name)
        )

    for doc_endpoint in sorted(doc_endpoints, key=sort_key):
        ident = doc_endpoint.method, doc_endpoint.path
        if ident in seen_paths:
            raise ValueError(
                f"{ident} has already been defined.\n\n"
                f"This one: {doc_endpoint.operation_object}\n\n"
                f"The previous one: {seen_paths[ident]}\n\n"
            )
        seen_paths[ident] = doc_endpoint.operation_object
        spec.path(
            path=doc_endpoint.effective_path,
            operations={str(k): v for k, v in doc_endpoint.operation_object.items()},
        )

    del seen_paths
    return spec


def get_endpoints_for_version(
    api_version: APIVersion,
) -> tuple[list[Endpoint], list[EndpointDefinition]]:
    legacy_endpoints: list[Endpoint] = []
    versioned_endpoints: list[EndpointDefinition] = []

    all_endpoints = discover_endpoints(api_version)

    for endpoint in all_endpoints.values():
        if isinstance(endpoint, Endpoint):
            legacy_endpoints.append(endpoint)
        else:
            versioned_endpoints.append(endpoint)

    return legacy_endpoints, versioned_endpoints


_SECURITY_SCHEMES = {
    "headerAuth": {
        "type": "http",
        "scheme": "bearer",
        "description": "Use user credentials in the `Authorization` HTTP header. "
        "The format of the header value is `$user $password`. This method has the "
        "highest precedence. If authentication succeeds, `cookieAuth` will be skipped.",
        "bearerFormat": "username password",
    },
    "webserverAuth": {
        "type": "http",
        "scheme": "basic",
        "description": "Use the authentication method of the webserver ('basic' or 'digest'). To "
        "use this, you'll either have to re-configure the site's Apache instance by yourself. "
        "If authentication succeeds, `cookieAuth` will be skipped.",
    },
}


def _make_spec(version: APIVersion) -> APISpec:
    spec = APISpec(
        "Checkmk REST-API",
        f"{version.numeric_value}.0",
        "3.1.1",
        plugins=[
            CheckmkPydanticPlugin(),
            MarshmallowPlugin(),
            apispec_oneofschema.MarshmallowPlugin(),
            CheckmkMarshmallowPlugin(),
        ],
        **_redoc_spec(),
    )

    for sec_scheme_name, sec_scheme_spec in _SECURITY_SCHEMES.items():
        spec.components.security_scheme(sec_scheme_name, sec_scheme_spec)

    # All the supported response headers by the spec.

    # response_headers = {
    #     'Allow',
    #     'Cache-Control',
    #     'Last-Modified',
    #     'Warning',
    #     'Content-Type',
    # }
    for header_name, field in ACCEPT_HEADER.items():
        spec.components.parameter(
            header_name,
            "header",
            dict(marshmallow_to_openapi([{header_name: field}], "header")[0]),
        )

    return spec


class OpenAPIInfoDict(TypedDict, total=True):
    description: str
    license: dict[str, str]
    contact: dict[str, str]


class TagGroup(TypedDict, total=True):
    name: str
    tags: list[str]


ReDocSpec = TypedDict(
    "ReDocSpec",
    {
        "info": OpenAPIInfoDict,
        "externalDocs": dict[str, str],
        "security": list[dict[str, list[str]]],
        "x-logo": dict[str, str],
        "x-tagGroups": list[TagGroup],
        "x-ignoredHeaderParameters": list[str],
    },
    total=True,
)


def _redoc_spec() -> ReDocSpec:
    return {
        "info": {
            "description": apispec_utils.dedent(__doc__)
            .strip()
            .replace("$TABLE_DEFINITIONS", "\n".join(table_definitions())),
            "license": {
                "name": "GNU General Public License version 2",
                "url": "https://checkmk.com/legal/gpl",
            },
            "contact": {
                "name": "Contact the Checkmk Team",
                "url": "https://checkmk.com/contact",
                "email": "feedback@checkmk.com",
            },
        },
        "externalDocs": {
            "description": "The official Checkmk user guide",
            "url": "https://docs.checkmk.com/",
        },
        "x-logo": {
            "url": "https://checkmk.com/bilder/brand-assets/checkmk_logo_main.png",
            "altText": "Checkmk",
        },
        "x-tagGroups": [
            {"name": "Monitoring", "tags": []},
            {"name": "Setup", "tags": []},
            {"name": "Checkmk Internal", "tags": []},
            {"name": "Undocumented Endpoint", "tags": []},
        ],
        "x-ignoredHeaderParameters": [
            "User-Agent",
            "X-Test-Header",
        ],
        "security": [{sec_scheme_name: []} for sec_scheme_name in _SECURITY_SCHEMES],
    }


def _add_cookie_auth(check_dict: dict[str, Any], site: SiteId) -> None:
    """Add the cookie authentication schema to the spec.

    We do this here, because every site has a different cookie name and such can't be predicted
    before this code here actually runs.
    """
    schema_name = "cookieAuth"
    _add_once(check_dict["security"], {schema_name: []})
    check_dict["components"]["securitySchemes"][schema_name] = {
        "in": "cookie",
        "name": f"auth_{site}",
        "type": "apiKey",
        "description": "Any user of Checkmk, who has already logged in, and thus got a cookie "
        "assigned, can use the REST API. Some actions may or may not succeed due "
        "to group and permission restrictions. This authentication method has the"
        "least precedence.",
    }


def _add_once(coll: list[dict[str, Any]], to_add: dict[str, Any]) -> None:
    """Add an entry to a collection, only once.

    Examples:

        >>> l = []
        >>> _add_once(l, {'foo': []})
        >>> l
        [{'foo': []}]

        >>> _add_once(l, {'foo': []})
        >>> l
        [{'foo': []}]

    Args:
        coll:
        to_add:

    Returns:

    """
    if to_add in coll:
        return None

    coll.append(to_add)
    return None
