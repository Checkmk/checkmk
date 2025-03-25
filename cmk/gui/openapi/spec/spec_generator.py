#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
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

import enum
import hashlib
import http.client
from collections.abc import Iterator, Sequence
from typing import Any, get_args, TypedDict

import apispec
import apispec_oneofschema
import openapi_spec_validator
from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin
from apispec.utils import dedent
from marshmallow import Schema
from marshmallow.schema import SchemaMeta
from werkzeug.utils import import_string

from livestatus import SiteId

from cmk.ccc import store
from cmk.ccc import version as cmk_version
from cmk.ccc.site import omd_site

from cmk.utils.paths import omd_root

from cmk.gui import main_modules
from cmk.gui.config import active_config
from cmk.gui.fields import Field
from cmk.gui.openapi.restful_objects.api_error import (
    api_custom_error_schema,
    api_default_error_schema,
)
from cmk.gui.openapi.restful_objects.code_examples import code_samples
from cmk.gui.openapi.restful_objects.decorators import Endpoint
from cmk.gui.openapi.restful_objects.documentation import table_definitions
from cmk.gui.openapi.restful_objects.endpoint_family import endpoint_family_registry
from cmk.gui.openapi.restful_objects.parameters import (
    ACCEPT_HEADER,
    CONTENT_TYPE,
    ETAG_HEADER_PARAM,
    ETAG_IF_MATCH_HEADER,
    HEADER_CHECKMK_EDITION,
    HEADER_CHECKMK_VERSION,
)
from cmk.gui.openapi.restful_objects.params import to_openapi
from cmk.gui.openapi.restful_objects.registry import endpoint_registry
from cmk.gui.openapi.restful_objects.type_defs import (
    ContentObject,
    EndpointTarget,
    ErrorStatusCodeInt,
    LocationType,
    OpenAPIParameter,
    OpenAPITag,
    OperationObject,
    OperationSpecType,
    PathItem,
    RawParameter,
    ResponseType,
    SchemaParameter,
    StatusCodeInt,
)
from cmk.gui.openapi.spec.plugin_marshmallow import CheckmkMarshmallowPlugin
from cmk.gui.openapi.spec.utils import spec_path
from cmk.gui.permissions import permission_registry
from cmk.gui.session import SuperUserContext
from cmk.gui.utils import get_failed_plugins
from cmk.gui.utils import permission_verification as permissions
from cmk.gui.utils.script_helpers import gui_context

Ident = tuple[str, str]
__version__ = "1.0"


def main() -> int:
    main_modules.load_plugins()
    if errors := get_failed_plugins():
        raise Exception(f"The following errors occured during plug-in loading: {errors}")

    with gui_context(), SuperUserContext():
        for target in get_args(EndpointTarget):
            store.save_object_to_file(
                spec_path(target),
                _generate_spec(_make_spec(), target, omd_site()),
                pretty=False,
            )
    return 0


def _generate_spec(
    spec: APISpec, target: EndpointTarget, site: SiteId, validate: bool = True
) -> dict[str, Any]:
    endpoint: Endpoint

    methods = ["get", "put", "post", "delete"]

    undocumented_tag_groups = ["Undocumented Endpoint"]

    if cmk_version.edition(omd_root) == cmk_version.Edition.CSE:
        undocumented_tag_groups.append("Checkmk Internal")

    def module_name(func: Any) -> str:
        return f"{func.__module__}.{func.__name__}"

    def sort_key(e: Endpoint) -> tuple[str | int, ...]:
        return e.sort, module_name(e.func), methods.index(e.method), e.path

    seen_paths: dict[Ident, OperationObject] = {}
    ident: Ident
    for endpoint in sorted(endpoint_registry, key=sort_key):
        if target in endpoint.blacklist_in or endpoint.tag_group in undocumented_tag_groups:
            continue

        for path, operation_dict in _operation_dicts(spec, endpoint):
            ident = endpoint.method, path
            if ident in seen_paths:
                raise ValueError(
                    f"{ident} has already been defined.\n\n"
                    f"This one: {operation_dict}\n\n"
                    f"The previous one: {seen_paths[ident]}\n\n"
                )
            seen_paths[ident] = operation_dict
            spec.path(path=path, operations={str(k): v for k, v in operation_dict.items()})

    del seen_paths

    generated_spec = spec.to_dict()
    _add_cookie_auth(generated_spec, site)
    if not validate:
        return generated_spec

    # TODO: Need to investigate later what is going on here after cleaning up a bit further
    openapi_spec_validator.validate(generated_spec)  # type: ignore[arg-type]
    return generated_spec


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


def _make_spec() -> apispec.APISpec:
    spec = apispec.APISpec(
        "Checkmk REST-API",
        __version__,
        "3.0.2",
        plugins=[
            MarshmallowPlugin(),
            apispec_oneofschema.MarshmallowPlugin(),  # type: ignore[attr-defined]
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
            dict(to_openapi([{header_name: field}], "header")[0]),
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
            "description": apispec.utils.dedent(__doc__)
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


def _operation_dicts(spec: APISpec, endpoint: Endpoint) -> Iterator[tuple[str, OperationObject]]:
    """Generate the openapi spec part of this endpoint.

    The result needs to be added to the `apispec` instance manually.
    """
    deprecate_self: bool = False
    if endpoint.deprecated_urls is not None:
        for url, werk_id in endpoint.deprecated_urls.items():
            deprecate_self |= url == endpoint.path
            yield url, _to_operation_dict(spec, endpoint, werk_id)

    if not deprecate_self:
        yield endpoint.path, _to_operation_dict(spec, endpoint)


class DefaultStatusCodeDescription(enum.Enum):
    Code406 = "The requests accept headers can not be satisfied."
    Code401 = "The user is not authorized to do this request."
    Code403 = "Configuration via Setup is disabled."
    Code404 = "The requested object has not be found."
    Code422 = "The request could not be processed."
    Code423 = "The resource is currently locked."
    Code405 = "Method not allowed: This request is only allowed with other HTTP methods."
    Code409 = "The request is in conflict with the stored resource."
    Code415 = "The submitted content-type is not supported."
    Code302 = (
        "Either the resource has moved or has not yet completed. "
        "Please see this resource for further information."
    )
    Code400 = "Parameter or validation failure."
    Code412 = "The value of the If-Match header doesn't match the object's ETag."
    Code428 = "The required If-Match header is missing."
    Code200 = "The operation was done successfully."
    Code204 = "Operation done successfully. No further output."


DEFAULT_STATUS_CODE_SCHEMAS = {
    (406, DefaultStatusCodeDescription.Code406): api_default_error_schema(
        406,
        DefaultStatusCodeDescription.Code406.value,
    ),
    (401, DefaultStatusCodeDescription.Code401): api_default_error_schema(
        401,
        DefaultStatusCodeDescription.Code401.value,
    ),
    (403, DefaultStatusCodeDescription.Code403): api_default_error_schema(
        403,
        DefaultStatusCodeDescription.Code403.value,
    ),
    (404, DefaultStatusCodeDescription.Code404): api_default_error_schema(
        404,
        DefaultStatusCodeDescription.Code404.value,
    ),
    (422, DefaultStatusCodeDescription.Code422): api_default_error_schema(
        422,
        DefaultStatusCodeDescription.Code422.value,
    ),
    (423, DefaultStatusCodeDescription.Code423): api_default_error_schema(
        423,
        DefaultStatusCodeDescription.Code423.value,
    ),
    (405, DefaultStatusCodeDescription.Code405): api_default_error_schema(
        405,
        DefaultStatusCodeDescription.Code405.value,
    ),
    (409, DefaultStatusCodeDescription.Code409): api_default_error_schema(
        409,
        DefaultStatusCodeDescription.Code409.value,
    ),
    (415, DefaultStatusCodeDescription.Code415): api_default_error_schema(
        415,
        DefaultStatusCodeDescription.Code415.value,
    ),
    (400, DefaultStatusCodeDescription.Code400): api_default_error_schema(
        400,
        DefaultStatusCodeDescription.Code400.value,
    ),
    (412, DefaultStatusCodeDescription.Code412): api_default_error_schema(
        412,
        DefaultStatusCodeDescription.Code412.value,
    ),
    (428, DefaultStatusCodeDescription.Code428): api_default_error_schema(
        428,
        DefaultStatusCodeDescription.Code428.value,
    ),
}


def _to_operation_dict(
    spec: APISpec,
    endpoint: Endpoint,
    werk_id: int | None = None,
) -> OperationObject:
    assert endpoint.func is not None, "This object must be used in a decorator environment."
    assert endpoint.operation_id is not None, "This object must be used in a decorator environment."

    module_obj = import_string(endpoint.func.__module__)

    response_headers: dict[str, OpenAPIParameter] = {}
    for header_to_add in [CONTENT_TYPE, HEADER_CHECKMK_EDITION, HEADER_CHECKMK_VERSION]:
        openapi_header = to_openapi([header_to_add], "header")[0]
        del openapi_header["in"]
        response_headers[openapi_header.pop("name")] = openapi_header

    if endpoint.etag in ("output", "both"):
        etag_header = to_openapi([ETAG_HEADER_PARAM], "header")[0]
        del etag_header["in"]
        response_headers[etag_header.pop("name")] = etag_header

    responses: ResponseType = {}

    responses["406"] = _error_response_path_item(
        endpoint, 406, DefaultStatusCodeDescription.Code406
    )

    if 401 in endpoint.expected_status_codes:
        responses["401"] = _error_response_path_item(
            endpoint, 401, DefaultStatusCodeDescription.Code401
        )

    if 403 in endpoint.expected_status_codes:
        responses["403"] = _error_response_path_item(
            endpoint, 403, DefaultStatusCodeDescription.Code403
        )

    if 404 in endpoint.expected_status_codes:
        responses["404"] = _error_response_path_item(
            endpoint, 404, DefaultStatusCodeDescription.Code404
        )

    if 422 in endpoint.expected_status_codes:
        responses["422"] = _error_response_path_item(
            endpoint, 422, DefaultStatusCodeDescription.Code422
        )

    if 423 in endpoint.expected_status_codes:
        responses["423"] = _error_response_path_item(
            endpoint, 423, DefaultStatusCodeDescription.Code423
        )

    if 405 in endpoint.expected_status_codes:
        responses["405"] = _error_response_path_item(
            endpoint, 405, DefaultStatusCodeDescription.Code405
        )

    if 409 in endpoint.expected_status_codes:
        responses["409"] = _error_response_path_item(
            endpoint, 409, DefaultStatusCodeDescription.Code409
        )

    if 415 in endpoint.expected_status_codes:
        responses["415"] = _error_response_path_item(
            endpoint, 415, DefaultStatusCodeDescription.Code415
        )

    if 302 in endpoint.expected_status_codes:
        responses["302"] = _path_item(endpoint, 302, DefaultStatusCodeDescription.Code302.value)

    if 303 in endpoint.expected_status_codes:
        responses["303"] = _path_item(endpoint, 303, DefaultStatusCodeDescription.Code302.value)

    if 400 in endpoint.expected_status_codes:
        responses["400"] = _error_response_path_item(
            endpoint, 400, DefaultStatusCodeDescription.Code400
        )

    # We don't(!) support any endpoint without an output schema.
    # Just define one!
    if 200 in endpoint.expected_status_codes:
        if endpoint.response_schema:
            content: ContentObject
            content = {endpoint.content_type: {"schema": endpoint.response_schema}}
        elif endpoint.content_type.startswith("application/") or endpoint.content_type.startswith(
            "image/"
        ):
            content = {
                endpoint.content_type: {
                    "schema": {
                        "type": "string",
                        "format": "binary",
                    }
                }
            }
        else:
            raise ValueError(f"Unknown content-type: {endpoint.content_type} Please add condition.")
        responses["200"] = _path_item(
            endpoint,
            200,
            DefaultStatusCodeDescription.Code200.value,
            content=content,
            headers=response_headers,
        )

    if 204 in endpoint.expected_status_codes:
        responses["204"] = _path_item(endpoint, 204, DefaultStatusCodeDescription.Code204.value)

    if 412 in endpoint.expected_status_codes:
        responses["412"] = _error_response_path_item(
            endpoint, 412, DefaultStatusCodeDescription.Code412
        )

    if 428 in endpoint.expected_status_codes:
        responses["428"] = _error_response_path_item(
            endpoint, 428, DefaultStatusCodeDescription.Code428
        )

    family_name = None
    tag_obj: OpenAPITag
    if endpoint.family_name is not None:
        family = endpoint_family_registry.get(endpoint.family_name)
        if family is not None:
            tag_obj = family.to_openapi_tag()
            family_name = family.name
            _add_tag(spec, tag_obj, tag_group=endpoint.tag_group)
    else:
        docstring_name = _docstring_name(module_obj.__doc__)
        tag_obj = {
            "name": docstring_name,
            "x-displayName": docstring_name,
        }
        docstring_desc = _docstring_description(module_obj.__doc__)
        if docstring_desc:
            tag_obj["description"] = docstring_desc

        family_name = docstring_name
        _add_tag(spec, tag_obj, tag_group=endpoint.tag_group)

    assert family_name is not None
    operation_spec: OperationSpecType = {
        "tags": [family_name],
        "description": "",
    }
    if werk_id:
        operation_spec["deprecated"] = True
        # ReDoc uses operationIds to build its URLs, so it needs a unique operationId,
        # otherwise links won't work properly.
        operation_spec["operationId"] = f"{endpoint.operation_id}-{werk_id}"
    else:
        operation_spec["operationId"] = endpoint.operation_id

    header_params: list[RawParameter] = []
    query_params: Sequence[RawParameter] = (
        endpoint.query_params if endpoint.query_params is not None else []
    )
    path_params: Sequence[RawParameter] = (
        endpoint.path_params if endpoint.path_params is not None else []
    )

    if active_config.rest_api_etag_locking and endpoint.etag in ("input", "both"):
        header_params.append(ETAG_IF_MATCH_HEADER)

    if endpoint.request_schema:
        header_params.append(CONTENT_TYPE)

    # While we define the parameters separately to be able to use them for validation, the
    # OpenAPI spec expects them to be listed in on place, so here we bunch them together.
    operation_spec["parameters"] = _coalesce_schemas(
        [
            ("header", header_params),
            ("query", query_params),
            ("path", path_params),
        ]
    )

    operation_spec["responses"] = responses

    if endpoint.request_schema is not None:
        operation_spec["requestBody"] = {
            "required": True,
            "content": {
                "application/json": {
                    "schema": endpoint.request_schema,
                }
            },
        }

    operation_spec["x-codeSamples"] = code_samples(
        spec,
        endpoint,
        header_params=header_params,
        path_params=path_params,
        query_params=query_params,
    )

    # If we don't have any parameters we remove the empty list, so the spec will not have it.
    if not operation_spec["parameters"]:
        del operation_spec["parameters"]

    try:
        docstring_name = _docstring_name(endpoint.func.__doc__)
    except ValueError as exc:
        raise ValueError(
            f"Function {module_obj.__name__}:{endpoint.func.__name__} has no docstring."
        ) from exc

    if docstring_name:
        operation_spec["summary"] = docstring_name
    else:
        raise RuntimeError(f"Please put a docstring onto {endpoint.operation_id}")

    if description := _build_description(_docstring_description(endpoint.func.__doc__), werk_id):
        # The validator will complain on empty descriptions being set, even though it's valid.
        operation_spec["description"] = description

    if endpoint.permissions_required is not None:
        # Check that all the names are known to the system.
        for perm in endpoint.permissions_required.iter_perms():
            if isinstance(perm, permissions.OkayToIgnorePerm):
                continue

            if perm.name not in permission_registry:
                # NOTE:
                #   See rest_api.py. dynamic_permission() have to be loaded before request
                #   for this to work reliably.
                raise RuntimeError(
                    f'Permission "{perm}" is not registered in the permission_registry.'
                )

        # Write permission documentation in openapi spec.
        if description := _permission_descriptions(
            endpoint.permissions_required, endpoint.permissions_description
        ):
            operation_spec.setdefault("description", "")
            if not operation_spec["description"]:
                operation_spec["description"] += "\n\n"
            operation_spec["description"] += description

    return {endpoint.method: operation_spec}


def _build_description(description_text: str | None, werk_id: int | None = None) -> str:
    r"""Build a OperationSpecType description.

    Examples:

        >>> _build_description(None)
        ''

        >>> _build_description("Foo")
        'Foo'

        >>> _build_description(None, 12345)
        '`WARNING`: This URL is deprecated, see [Werk 12345](https://checkmk.com/werk/12345) for more details.\n\n'

        >>> _build_description('Foo', 12345)
        '`WARNING`: This URL is deprecated, see [Werk 12345](https://checkmk.com/werk/12345) for more details.\n\nFoo'

    Args:
        description_text:
            The text of the description. This may be None.

        werk_id:
            A Werk ID for a deprecation warning. This may be None.

    Returns:
        Either a complete description or None

    """
    if werk_id:
        werk_link = f"https://checkmk.com/werk/{werk_id}"
        description = (
            f"`WARNING`: This URL is deprecated, see [Werk {werk_id}]({werk_link}) for more "
            "details.\n\n"
        )
    else:
        description = ""

    if description_text is not None:
        description += description_text

    return description


def _permission_descriptions(
    perms: permissions.BasePerm,
    descriptions: dict[str, str] | None = None,
) -> str:
    r"""Describe permissions human-readable

    Args:
        perms:
        descriptions:

    Examples:

        >>> _permission_descriptions(
        ...     permissions.Perm("wato.edit_folders"),
        ...     {'wato.edit_folders': 'Allowed to cook the books.'},
        ... )
        'This endpoint requires the following permissions: \n * `wato.edit_folders`: Allowed to cook the books.\n'

        >>> _permission_descriptions(
        ...     permissions.AllPerm([permissions.Perm("wato.edit_folders")]),
        ...     {'wato.edit_folders': 'Allowed to cook the books.'},
        ... )
        'This endpoint requires the following permissions: \n * `wato.edit_folders`: Allowed to cook the books.\n'

        >>> _permission_descriptions(
        ...     permissions.AllPerm([permissions.Perm("wato.edit_folders"),
        ...                          permissions.Undocumented(permissions.Perm("wato.edit"))]),
        ...     {'wato.edit_folders': 'Allowed to cook the books.'},
        ... )
        'This endpoint requires the following permissions: \n * `wato.edit_folders`: Allowed to cook the books.\n'

        >>> _permission_descriptions(
        ...     permissions.AnyPerm([permissions.Perm("wato.edit_folders"), permissions.Perm("wato.edit_folders")]),
        ...     {'wato.edit_folders': 'Allowed to cook the books.'},
        ... )
        'This endpoint requires the following permissions: \n * Any of:\n   * `wato.edit_folders`: Allowed to cook the books.\n   * `wato.edit_folders`: Allowed to cook the books.\n'

        The description will have a structure like this:

            * Any of:
               * c
               * All of:
                  * a
                  * b

        >>> _permission_descriptions(
        ...     permissions.AnyPerm([
        ...         permissions.Perm("c"),
        ...         permissions.AllPerm([
        ...              permissions.Perm("a"),
        ...              permissions.Perm("b"),
        ...         ]),
        ...     ]),
        ...     {'a': 'Hold a', 'b': 'Hold b', 'c': 'Hold c'}
        ... )
        'This endpoint requires the following permissions: \n * Any of:\n   * `c`: Hold c\n   * All of:\n     * `a`: Hold a\n     * `b`: Hold b\n'

    Returns:
        The description as a string.

    """
    description_map: dict[str, str] = descriptions if descriptions is not None else {}
    _description: list[str] = ["This endpoint requires the following permissions: "]

    def _count_perms(_perms):
        return len([p for p in _perms if not isinstance(p, permissions.Undocumented)])

    def _add_desc(permission: permissions.BasePerm, indent: int, desc_list: list[str]) -> None:
        if isinstance(permission, permissions.Undocumented):
            # Don't render
            return

        # We indent by two spaces, as is required by markdown.
        prefix = "  " * indent
        if isinstance(permission, (permissions.Perm, permissions.OkayToIgnorePerm)):
            perm_name = permission.name
            try:
                desc = description_map.get(perm_name) or permission_registry[perm_name].description
            except KeyError:
                if isinstance(permission, permissions.OkayToIgnorePerm):
                    return
                raise
            _description.append(f"{prefix} * `{perm_name}`: {desc}")
        elif isinstance(permission, permissions.AllPerm):
            # If AllOf only contains one permission, we don't need to show the AllOf
            if _count_perms(permission.perms) == 1:
                _add_desc(permission.perms[0], indent, desc_list)
            else:
                desc_list.append(f"{prefix} * All of:")
                for perm in permission.perms:
                    _add_desc(perm, indent + 1, desc_list)
        elif isinstance(permission, permissions.AnyPerm):
            # If AnyOf only contains one permission, we don't need to show the AnyOf
            if _count_perms(permission.perms) == 1:
                _add_desc(permission.perms[0], indent, desc_list)
            else:
                desc_list.append(f"{prefix} * Any of:")
                for perm in permission.perms:
                    _add_desc(perm, indent + 1, desc_list)
        elif isinstance(permission, permissions.Optional):
            desc_list.append(f"{prefix} * Optionally:")
            _add_desc(permission.perm, indent + 1, desc_list)
        else:
            raise NotImplementedError(f"Printing of {permission!r} not yet implemented.")

    _add_desc(perms, 0, _description)
    return "\n".join(_description) + "\n"


def _path_item(
    endpoint: Endpoint,
    status_code: StatusCodeInt,
    description: str,
    content: dict[str, Any] | None = None,
    headers: dict[str, OpenAPIParameter] | None = None,
) -> PathItem:
    if status_code in endpoint.status_descriptions:
        description = endpoint.status_descriptions[status_code]

    response: PathItem = {
        "description": f"{http.client.responses[status_code]}: {description}",
        "content": content if content is not None else {},
    }
    if headers:
        response["headers"] = headers
    return response


def _error_response_path_item(
    endpoint: Endpoint,
    status_code: ErrorStatusCodeInt,
    default_description: DefaultStatusCodeDescription,
) -> PathItem:
    description = default_description.value
    schema = DEFAULT_STATUS_CODE_SCHEMAS.get((status_code, default_description))
    if status_code in endpoint.status_descriptions:
        description = endpoint.status_descriptions[status_code]
        schema = api_custom_error_schema(status_code, description)

    error_schema = endpoint.error_schemas.get(status_code, schema)
    response: PathItem = {
        "description": f"{http.client.responses[status_code]}: {description}",
        "content": {"application/problem+json": {"schema": error_schema}},
    }
    return response


def _coalesce_schemas(
    parameters: Sequence[tuple[LocationType, Sequence[RawParameter]]],
) -> Sequence[SchemaParameter]:
    rv: list[SchemaParameter] = []
    for location, params in parameters:
        if not params:
            continue

        to_convert: dict[str, Field] = {}
        for param in params:
            if isinstance(param, SchemaMeta):
                rv.append({"in": location, "schema": param})
            else:
                to_convert.update(param)

        if to_convert:
            rv.append({"in": location, "schema": _to_named_schema(to_convert)})

    return rv


def _patch_regex(fields: dict[str, Field]) -> dict[str, Field]:
    for _, value in fields.items():
        if "pattern" in value.metadata and value.metadata["pattern"].endswith(r"\Z"):
            value.metadata["pattern"] = value.metadata["pattern"][:-2] + "$"
    return fields


def _to_named_schema(fields_: dict[str, Field]) -> type[Schema]:
    attrs: dict[str, Any] = _patch_regex(fields_.copy())
    attrs["Meta"] = type(
        "GeneratedMeta",
        (Schema.Meta,),
        {"register": True},
    )
    _hash = hashlib.sha256()

    def _update(d_):
        for key, value in sorted(d_.items()):
            _hash.update(str(key).encode("utf-8"))
            if hasattr(value, "metadata"):
                _update(value.metadata)
            else:
                _hash.update(str(value).encode("utf-8"))

    _update(fields_)

    name = f"GeneratedSchema{_hash.hexdigest()}"
    schema_cls: type[Schema] = type(name, (Schema,), attrs)
    return schema_cls


def _add_tag(spec: APISpec, tag: OpenAPITag, tag_group: str | None = None) -> None:
    name = tag["name"]
    if name in [t["name"] for t in spec._tags]:
        return

    spec.tag(dict(tag))
    if tag_group is not None:
        _assign_to_tag_group(spec, tag_group, name)


def _assign_to_tag_group(spec: APISpec, tag_group: str, name: str) -> None:
    for group in spec.options.setdefault("x-tagGroups", []):
        if group["name"] == tag_group:
            group["tags"].append(name)
            break
    else:
        raise ValueError(f"x-tagGroup {tag_group} not found. Please add it to specification.py")


def _docstring_description(docstring: str | None) -> str | None:
    """Split the docstring by title and rest.

    This is part of the rest.

    >>> _docstring_description(_docstring_description.__doc__).split("\\n")[0]
    'This is part of the rest.'

    Args:
        docstring:

    Returns:
        A string or nothing.

    """
    if not docstring:
        return None
    parts = dedent(docstring).split("\n\n", 1)
    if len(parts) > 1:
        return parts[1].strip()
    return None


def _docstring_name(docstring: str | None) -> str:
    """Split the docstring by title and rest.

    This is part of the rest.

    >>> _docstring_name(_docstring_name.__doc__)
    'Split the docstring by title and rest.'

    >>> _docstring_name("")
    Traceback (most recent call last):
    ...
    ValueError: No name for the module defined. Please add a docstring!

    Args:
        docstring:

    Returns:
        A string or nothing.

    """
    if not docstring:
        raise ValueError("No name for the module defined. Please add a docstring!")

    return [part.strip() for part in dedent(docstring).split("\n\n", 1)][0]


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
