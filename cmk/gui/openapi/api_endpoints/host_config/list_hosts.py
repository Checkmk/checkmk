#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Annotated, Literal

from cmk.gui.logged_in import user
from cmk.gui.openapi.api_endpoints.host_config.models.response_models import (
    HostConfigModel,
)
from cmk.gui.openapi.api_endpoints.host_config.utils import serialize_host
from cmk.gui.openapi.framework import QueryParam
from cmk.gui.openapi.framework.api_config import APIVersion
from cmk.gui.openapi.framework.model import api_field, ApiOmitted
from cmk.gui.openapi.framework.model.base_models import DomainObjectCollectionModel, LinkModel
from cmk.gui.openapi.framework.model.common_fields import FieldsFilterType
from cmk.gui.openapi.framework.versioned_endpoint import (
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.restful_objects.constructors import collection_href
from cmk.gui.openapi.shared_endpoint_families.host_config import HOST_CONFIG_FAMILY
from cmk.gui.utils import permission_verification as permissions
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


class SearchFilter:
    def __init__(
        self,
        hostnames: Sequence[str] | None,
        site: str | None,
    ) -> None:
        self._hostnames = set(hostnames) if hostnames else None
        self._site = site

    def __call__(self, host: Host) -> bool:
        return self.filter_by_hostnames(host) and self.filter_by_site(host)

    def filter_by_hostnames(self, host: Host) -> bool:
        return host.name() in self._hostnames if self._hostnames else True

    def filter_by_site(self, host: Host) -> bool:
        return host.site_id() == self._site if self._site else True


def list_hosts_v1(
    fields: FieldsFilterType = ApiOmitted(),
    effective_attributes: Annotated[
        bool,
        QueryParam(
            description="Show all effective attributes on hosts, not just the attributes which were set on "
            "this host specifically. This includes all attributes of all of this host's parent "
            "folders.",
            example="False",
        ),
    ] = False,
    include_links: Annotated[
        bool,
        QueryParam(
            description="Flag which toggles whether the links field of the individual values should be populated.",
            example="False",
        ),
    ] = False,
    hostnames: Annotated[
        list[str] | ApiOmitted,
        QueryParam(
            description="A list of host names to filter the result by.",
            example="host1",
            is_list=True,
        ),
    ] = ApiOmitted(),
    site: Annotated[
        str | ApiOmitted,
        QueryParam(description="Filter the result by a specific site.", example="site1"),
    ] = ApiOmitted(),
) -> HostConfigCollectionModel:
    """Show all hosts"""
    root_folder = folder_tree().root_folder()
    hosts_filter = SearchFilter(
        hostnames=None if isinstance(hostnames, ApiOmitted) else hostnames,
        site=None if isinstance(site, ApiOmitted) else site,
    )
    if user.may("wato.see_all_folders"):
        # allowed to see all hosts, no need for individual permission checks
        hosts: Iterable[Host] = root_folder.all_hosts_recursively().values()
    else:
        hosts = _iter_hosts_with_permission(root_folder)
    with tracer.span("list-hosts-build-response"):
        return HostConfigCollectionModel(
            domainType="host_config",
            id="host",
            extensions=ApiOmitted(),
            value=[
                serialize_host(
                    host=host,
                    compute_links=include_links,
                    compute_effective_attributes=effective_attributes,
                )
                for host in filter(hosts_filter, hosts)
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
        path=collection_href("host_config"),
        link_relation=".../collection",
        method="get",
    ),
    permissions=EndpointPermissions(
        required=permissions.Optional(permissions.Perm("wato.see_all_folders"))
    ),
    doc=EndpointDoc(family=HOST_CONFIG_FAMILY.name),
    versions={APIVersion.UNSTABLE: EndpointHandler(handler=list_hosts_v1)},
)
