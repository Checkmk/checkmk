#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Iterable, Sequence
from typing import Annotated, NamedTuple

from cmk import trace
from cmk.gui.fields.fields_filter import FieldsFilter
from cmk.gui.logged_in import user
from cmk.gui.openapi.framework import (
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    QueryParam,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model import ApiOmitted
from cmk.gui.openapi.framework.model.common_fields import FieldsFilterType
from cmk.gui.openapi.restful_objects.constructors import collection_href
from cmk.gui.openapi.shared_endpoint_families.host_config import HOST_CONFIG_FAMILY
from cmk.gui.utils import permission_verification as permissions
from cmk.gui.watolib.hosts_and_folders import Folder, folder_tree, Host

from ._utils import serialize_host_collection
from .models.response_models import HostConfigCollectionModel

tracer = trace.get_tracer()


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


class _ComputeFields(NamedTuple):
    effective_attributes: bool
    links: bool


def _merge_filters(
    fields: FieldsFilter | ApiOmitted, compute_effective_attributes: bool, compute_links: bool
) -> _ComputeFields:
    """Merge the fields filter with the effective attributes and include links flags.

    The framework already handles the fields filter, we only care about specific fields for
    performance gains by not computing them when they are not requested."""
    if isinstance(fields, ApiOmitted):
        return _ComputeFields(
            effective_attributes=compute_effective_attributes,
            links=compute_links,
        )
    return _ComputeFields(
        effective_attributes=fields.is_included("extensions.effective_attributes"),
        links=fields.is_included("links"),
    )


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

    compute = _merge_filters(
        fields, compute_effective_attributes=effective_attributes, compute_links=include_links
    )
    with tracer.span("list-hosts-build-response"):
        return serialize_host_collection(
            [host for host in filter(hosts_filter, hosts)],
            compute_effective_attributes=compute.effective_attributes,
            compute_links=compute.links,
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
