#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field

from cmk.gui.http import HTTPMethod
from cmk.gui.openapi.framework.api_config import APIVersion
from cmk.gui.openapi.restful_objects.api_error import ApiError
from cmk.gui.openapi.restful_objects.decorators import AcceptFieldType
from cmk.gui.openapi.restful_objects.type_defs import (
    EndpointTarget,
    ErrorStatusCodeInt,
    ETagBehaviour,
    LinkRelation,
    StatusCodeInt,
    TagGroup,
)
from cmk.gui.utils import permission_verification as permissions


@dataclass(slots=True, frozen=True)
class EndpointHandler:
    """Endpoint body specific attributes

    Notes:
        * all attributes are version specific and can therefore change depending on the version

    Attributes:
        handler:
            The endpoint body function. This function is called when the endpoint is invoked.
            The function signature is used to parse the respective doc schemas as well as used
            for request and response validation

        error_schemas:
            A dictionary of error schemas. The keys are the HTTP status codes and the values
            are the schemas.

        status_descriptions:
            A dictionary of status code descriptions. The keys are the non-error HTTP status codes
    """

    # TODO: this needs to be extended with the dataclass syntax
    handler: Callable
    # TODO: ApiError needs to be changed to the equivalent dataclass error
    error_schemas: Mapping[ErrorStatusCodeInt, type[ApiError]] | None = None
    status_descriptions: dict[StatusCodeInt, str] | None = None
    additional_status_codes: Sequence[StatusCodeInt] | None = None


@dataclass(slots=True, frozen=True)
class EndpointMetadata:
    """Endpoint metadata properties

    Attributes:
        path:
            The URI. Can contain 0-N placeholders like this: /path/{placeholder1}/{placeholder2}.
            These variables have to be defined elsewhere first. See the {query,path,header}_params
            Arguments of this class.

        link_relation:
            The link relation of the endpoint. This relation is used to identify an endpoint
            for linking. This has to be unique in it's module.

        method:
            The HTTP method under which the endpoint should be accessible. Methods are written
            lowercase in the OpenAPI YAML-file, though both upper and lower-cased method-names
            are supported here.

        content_type:
            The content-type under which this endpoint shall be executed. Multiple endpoints may
            be defined for any one URL, but only one endpoint per url-content-type combination.

        accept:
            The content-type accepted by the endpoint
    """

    path: str
    link_relation: LinkRelation
    family: str
    method: HTTPMethod
    content_type: str = "application/json"
    accept: AcceptFieldType = "application/json"


@dataclass(slots=True, frozen=True)
class EndpointBehavior:
    """Properties that define the behavior of the endpoint during invocation. Some influence the
    behaviour on a REST API while others are more Checkmk specific.

    Attributes:
        etag:
            One of 'input', 'output', 'both'. When set to 'input' a valid ETag is required in
            the 'If-Match' request header. When set to 'output' a ETag is sent to the client
            with the 'ETag' response header. When set to 'both', it will act as if set to
            'input' and 'output' at the same time.

        skip_locking:
            When set to True, the decorator will not try to acquire a wato configuration lock,
            which can lead to higher performance of this particular endpoint. WARNING: Do not
            activate this flag when configuration files are changed by the endpoint! This
            exposes the data to potential race conditions. Use it for endpoints which trigger
            livestatus commands.

        update_config_generation:
            Whether to generate a new configuration. All endpoints with methods other than `get`
            normally trigger a regeneration of the configuration. This can be turned off by
            setting `update_config_generation` to False.

    """

    etag: ETagBehaviour | None = None
    skip_locking: bool = False
    update_config_generation: bool = True


@dataclass(slots=True, frozen=True)
class EndpointPermissions:
    """The Checkmk role permissions required to invoke this endpoint.

    Attributes:
        required:
            A declaration of the permissions required by this endpoint. This needs to be
            exhaustive in the sense that any permission which MAY be used by this endpoint NEEDS
            to be declared here!

            WARNING
                Failing to do so will result in runtime exceptions when an *undeclared*
                permission is required in the code.

            The combinators "Any" and "All" can be used to express more complex cases. For example:

                AnyPerm([All([Perm("wato.edit"), Perm("wato.access")]), Perm("wato.godmode")])

            This expresses that the endpoint requires either "wato.godmode" or "wato.access"
            and "wato.edit" at them same time. The nesting can be arbitrarily deep. For no access
            at all, NoPerm() can be used. Import these helpers from the `permissions` package.

        descriptions:
            All declared permissions are documented in the REST API documentation with their
            default description taken from the permission_registry. When you need a more
            descriptive permission description you can declare them with a dict.

            Example:

                {"wato.godmode": "You can do whatever you want!"}
    """

    required: permissions.BasePerm | None = None
    descriptions: Mapping[str, str] | None = None


@dataclass(slots=True, frozen=True)
class EndpointDoc:
    """Properties for the documentation of the endpoint.

    Attributes:
        group:
            The documentation group the endpoint belongs to.

        sort_index:
            The index used to sort the endpoint within the endpoint family

        exclude_in_targets:
            A set of endpoint documentation targets to exclude this endpoint from.
    """

    group: TagGroup = "Setup"
    sort_index: int = 0
    exclude_in_targets: set[EndpointTarget] = field(default_factory=set)


@dataclass(slots=True, frozen=True)
class VersionedEndpoint:
    """The structure of the versioned endpoint

    Versioning follows a bottom-up inheritance model. When a handler is not explicitly defined
    for a specific released version, the endpoint automatically inherits the handler from the
    most recent previously defined version. This creates a chain of fallbacks where each
    version potentially builds upon its predecessors.

    Versioning build example example:
        APIVersion.V1 (specified) -> APIVersion.V2 (not specified) -> APIVersion.V3 (specified)

        APIVersion.V2 will implicitly inherit the handler of the V1

    Legacy marshmallow endpoint:
        If an equivalent marshmallow endpoint exists then the marshmallow endpoint will represent the first
        released version (not necessarily APIVersion.V1) of the endpoint.

    Notes:
        * only the individual handlers are version specific
        * all other attributes such as metadata should not change across versions (e.g.
        changing the path of an endpoint would be rather a new endpoint instead). However, if
        a certain need for this arises, talk to the API team first.

    Attributes:
        metadata:
            The metadata properties of the endpoint

        permissions:
            The Checkmk role permissions required to invoke this endpoint

        doc:
            The REST API spec documentation properties of the endpoint

        versions:
            A mapping of the version to the version specific endpoint handler

        behavior:
            The REST API and Checkmk specific behavior properties of the endpoint

        removed_in_version:
            The starting (inclusive) version from which the endpoint will be no longer available
            in the REST-API. All subsequent REST API versions will also not include this
            endpoint.
    """

    # TODO: deprecation handling must be included (on a per version basis)
    metadata: EndpointMetadata
    permissions: EndpointPermissions
    doc: EndpointDoc
    versions: Mapping[APIVersion, EndpointHandler]
    behavior: EndpointBehavior
    removed_in_version: APIVersion | None = None
