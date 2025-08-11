#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence
from typing import Annotated

from cmk.gui.logged_in import user
from cmk.gui.openapi.api_endpoints.models.host_attribute_models import HostUpdateAttributeModel
from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointBehavior,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    PathParam,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model import api_field, api_model, ApiOmitted
from cmk.gui.openapi.framework.model.converter import HostConverter, TypedPlainValidator
from cmk.gui.openapi.framework.model.response import ApiResponse
from cmk.gui.openapi.restful_objects.constructors import object_href
from cmk.gui.openapi.shared_endpoint_families.host_config import HOST_CONFIG_FAMILY
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.watolib.configuration_bundle_store import is_locked_by_quick_setup
from cmk.gui.watolib.host_attributes import HostAttributes
from cmk.gui.watolib.hosts_and_folders import Host

from ._utils import host_etag, PERMISSIONS_UPDATE, serialize_host
from .models.response_models import HostConfigModel


@api_model
class UpdateHost:
    attributes: HostUpdateAttributeModel | ApiOmitted = api_field(
        description=(
            "Replace all currently set attributes on the host, with these attributes. "
            "Any previously set attributes which are not given here will be removed. "
            "Can't be used together with update_attributes or remove_attributes fields."
        ),
        example={"ipaddress": "192.168.0.123"},
        default_factory=ApiOmitted,
    )

    update_attributes: HostUpdateAttributeModel | ApiOmitted = api_field(
        description=(
            "Just update the hosts attributes with these attributes. The previously set "
            "attributes will be overwritten. Can't be used together with attributes or "
            "remove_attributes fields."
        ),
        example={"ipaddress": "192.168.0.123"},
        default_factory=ApiOmitted,
    )

    remove_attributes: list[str] | ApiOmitted = api_field(
        description=(
            "A list of attributes which should be removed. Can't be used together with "
            "attributes or update attributes fields."
        ),
        example=["tag_foobar"],
        default_factory=ApiOmitted,
    )

    def __post_init__(self) -> None:
        """Only one of the attributes field is allowed at a time."""
        data = {
            "attributes": self.attributes,
            "update_attributes": self.update_attributes,
            "remove_attributes": self.remove_attributes,
        }
        set_keys = [key for key, value in data.items() if not isinstance(value, ApiOmitted)]
        if len(set_keys) > 1:
            raise ValueError(
                f"This endpoint only allows 1 action (set/update/remove) per call, you specified {len(set_keys)} actions: {', '.join(set_keys)}."
            )


def validate_host_attributes_for_quick_setup(host: Host, body: UpdateHost) -> bool:
    if not is_locked_by_quick_setup(host.locked_by()):
        return True

    locked_attributes: Sequence[str] = host.attributes.get("locked_attributes", [])
    new_attributes: HostAttributes | None = (
        body.attributes.to_internal() if body.attributes else None
    )
    update_attributes: HostAttributes | None = (
        body.update_attributes.to_internal() if body.update_attributes else None
    )
    remove_attributes: Sequence[str] | None = body.remove_attributes or None

    if new_attributes and (
        new_attributes.get("locked_by") != host.attributes.get("locked_by")
        or new_attributes.get("locked_attributes") != locked_attributes
        or any(new_attributes.get(key) != host.attributes.get(key) for key in locked_attributes)
    ):
        return False

    if update_attributes and any(
        key in locked_attributes and host.attributes.get(key) != attr
        for key, attr in update_attributes.items()
    ):
        return False

    return not (remove_attributes and any(key in locked_attributes for key in remove_attributes))


def update_host_v1(
    api_context: ApiContext,
    body: UpdateHost,
    host: Annotated[
        Annotated[
            Host,
            TypedPlainValidator(str, HostConverter(permission_type="setup_write").host),
        ],
        PathParam(description="Host name", example="example.com", alias="host_name"),
    ],
) -> ApiResponse[HostConfigModel]:
    """Update a host"""
    user.need_permission("wato.edit")
    user.need_permission("wato.edit_hosts")
    if api_context.etag.enabled:
        api_context.etag.verify(host_etag(host))

    if not validate_host_attributes_for_quick_setup(host, body):
        raise ProblemException(
            status=400,
            title=f'The host "{host.name()}" is locked by Quick setup.',
            detail="Cannot modify locked attributes.",
        )

    if body.attributes:
        new_attributes = body.attributes.to_internal()
        new_attributes["meta_data"] = host.attributes.get("meta_data", {})
        host.edit(
            new_attributes,
            host.cluster_nodes(),
            pprint_value=api_context.config.wato_pprint_config,
            use_git=api_context.config.wato_use_git,
        )

    if body.update_attributes:
        host.update_attributes(
            body.update_attributes.to_internal(),
            pprint_value=api_context.config.wato_pprint_config,
            use_git=api_context.config.wato_use_git,
        )

    if body.remove_attributes:
        faulty_attributes = []
        for attribute in body.remove_attributes:
            if attribute not in host.attributes:
                faulty_attributes.append(attribute)

        host.clean_attributes(  # silently ignores missing attributes
            body.remove_attributes,
            pprint_value=api_context.config.wato_pprint_config,
            use_git=api_context.config.wato_use_git,
        )

        if faulty_attributes:
            raise ProblemException(
                status=400,
                title="Some attributes were not removed",
                detail=f"The following attributes were not removed since they didn't exist: {', '.join(faulty_attributes)}",
            )

    return ApiResponse(
        body=serialize_host(host, compute_effective_attributes=False, compute_links=True),
        etag=host_etag(host),
    )


ENDPOINT_UPDATE_HOST = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_href("host_config", "{host_name}"),
        link_relation=".../update",
        method="put",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS_UPDATE),
    doc=EndpointDoc(family=HOST_CONFIG_FAMILY.name),
    versions={APIVersion.UNSTABLE: EndpointHandler(handler=update_host_v1)},
    behavior=EndpointBehavior(etag="both"),
)
