#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Iterable
from dataclasses import dataclass
from typing import get_type_hints, Literal

from cmk.gui.logged_in import user
from cmk.gui.openapi.api_endpoints.host_config.models.response_models import (
    HostConfigModel,
    HostExtensionsModel,
)
from cmk.gui.openapi.api_endpoints.models.host_attribute_models import HostViewAttributeModel
from cmk.gui.openapi.framework.api_config import APIVersion
from cmk.gui.openapi.framework.model import api_field, ApiOmitted
from cmk.gui.openapi.framework.model.base_models import DomainObjectCollectionModel, LinkModel
from cmk.gui.openapi.framework.versioned_endpoint import (
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.restful_objects import constructors
from cmk.gui.openapi.restful_objects.constructors import collection_href
from cmk.gui.openapi.shared_endpoint_families.host_config import HOST_CONFIG_FAMILY
from cmk.gui.utils import permission_verification as permissions
from cmk.gui.watolib.host_attributes import HostAttributes
from cmk.gui.watolib.hosts_and_folders import Folder, folder_tree, Host

from cmk import trace

tracer = trace.get_tracer()


@dataclass(kw_only=True, slots=True)
class HostConfigCollectionModel(DomainObjectCollectionModel):
    domainType: Literal["host_config"] = api_field(
        description="The domain type of the objects in the collection",
        example="host_config",
    )
    # TODO: add proper example
    value: list[HostConfigModel] = api_field(description="A list of host objects", example="")


def list_hosts_v1() -> HostConfigCollectionModel:
    """Show all hosts"""
    root_folder = folder_tree().root_folder()
    if user.may("wato.see_all_folders"):
        # allowed to see all hosts, no need for individual permission checks
        hosts: Iterable[Host] = root_folder.all_hosts_recursively().values()
    else:
        hosts = _iter_hosts_with_permission(root_folder)
    static_attribute_names = set(get_type_hints(HostAttributes))
    with tracer.span("list-hosts-build-response"):
        return HostConfigCollectionModel(
            domainType="host_config",
            value=[
                HostConfigModel(
                    domainType="host_config",
                    title=host.alias() or host.name(),
                    # TODO: enable with filter build
                    links=[],
                    members=None,
                    extensions=HostExtensionsModel(
                        folder=host.folder().name(),
                        attributes=HostViewAttributeModel.from_internal(
                            host.attributes, static_attribute_names
                        ),
                        # TODO: enable with filter
                        effective_attributes=ApiOmitted(),
                        is_cluster=host.is_cluster(),
                        cluster_nodes=host.cluster_nodes(),
                    ),
                )
                for host in hosts
            ],
            links=[LinkModel.create("self", collection_href("host_config"))],
        )


def _iter_hosts_with_permission(folder: Folder) -> Iterable[Host]:
    yield from (host for host in folder.hosts().values() if host.permissions.may("read"))
    for subfolder in folder.subfolders():
        if not subfolder.permissions.may("read"):
            continue  # skip all hosts if folder isn't readable

        yield from _iter_hosts_with_permission(subfolder)


ENDPOINT_LIST_HOSTS = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=constructors.collection_href("host_config"),
        link_relation=".../collection",
        method="get",
    ),
    permissions=EndpointPermissions(
        required=permissions.Optional(permissions.Perm("wato.see_all_folders"))
    ),
    doc=EndpointDoc(family=HOST_CONFIG_FAMILY.name),
    versions={APIVersion.UNSTABLE: EndpointHandler(handler=list_hosts_v1)},
)
