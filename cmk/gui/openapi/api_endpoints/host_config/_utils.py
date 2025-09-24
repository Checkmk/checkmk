#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
from collections.abc import Callable, Iterable, Sequence
from typing import get_type_hints

from cmk.ccc.hostaddress import HostName
from cmk.gui.openapi.api_endpoints.models.host_attribute_models import HostViewAttributeModel
from cmk.gui.openapi.endpoints.utils import folder_slug
from cmk.gui.openapi.framework import ETag
from cmk.gui.openapi.framework.model import (
    ApiOmitted,
    json_dump_without_omitted,
)
from cmk.gui.openapi.framework.model.base_models import LinkModel
from cmk.gui.openapi.framework.model.constructors import generate_links
from cmk.gui.openapi.restful_objects import constructors
from cmk.gui.openapi.utils import EXT, ProblemException
from cmk.gui.utils import permission_verification as permissions
from cmk.gui.watolib.configuration_bundle_store import is_locked_by_quick_setup
from cmk.gui.watolib.host_attributes import HostAttributes
from cmk.gui.watolib.hosts_and_folders import Host

from .models.request_models import UpdateHost
from .models.response_models import (
    HostConfigCollectionModel,
    HostConfigModel,
    HostExtensionsModel,
)


class AgentLinkHook:
    create_links: Callable[[HostName], list[LinkModel]] = lambda h: []


_PERMISSIONS_RW_UNDOCUMENTED = permissions.Undocumented(
    permissions.AnyPerm(
        [
            permissions.OkayToIgnorePerm("bi.see_all"),
            permissions.Perm("general.see_all"),
            permissions.OkayToIgnorePerm("mkeventd.seeall"),
            # only used to check if user can see a host
            permissions.Perm("wato.see_all_folders"),
        ]
    )
)
PERMISSIONS = permissions.Optional(permissions.Perm("wato.see_all_folders"))
PERMISSIONS_CREATE = permissions.AllPerm(
    [
        permissions.Perm("wato.edit"),
        permissions.Perm("wato.manage_hosts"),
        permissions.Optional(permissions.Perm("wato.all_folders")),
        _PERMISSIONS_RW_UNDOCUMENTED,
    ]
)
PERMISSIONS_UPDATE = permissions.AllPerm(
    [
        permissions.Perm("wato.edit"),
        permissions.Perm("wato.edit_hosts"),
        permissions.Optional(permissions.Perm("wato.all_folders")),
        _PERMISSIONS_RW_UNDOCUMENTED,
    ]
)

_static_attribute_names = set(get_type_hints(HostAttributes))


def serialize_host(
    host: Host,
    *,
    compute_effective_attributes: bool,
    compute_links: bool,
) -> HostConfigModel:
    links = []
    if compute_links:
        links = generate_links("host_config", host.id())
        links.append(
            LinkModel.create(
                rel="cmk/folder_config",
                href=constructors.object_href("folder_config", folder_slug(host.folder())),
                method="get",
                title="The folder config of the host.",
            )
        )
        links.extend(AgentLinkHook.create_links(host.name()))

    return HostConfigModel(
        domainType="host_config",
        id=host.id(),
        title=host.alias() or host.name(),
        links=links,
        members=None,
        extensions=HostExtensionsModel(
            folder=host.folder(),
            attributes=HostViewAttributeModel.from_internal(
                host.attributes, _static_attribute_names
            ),
            effective_attributes=HostViewAttributeModel.from_internal(
                host.effective_attributes(), _static_attribute_names
            )
            if compute_effective_attributes
            else ApiOmitted(),
            is_cluster=host.is_cluster(),
            is_offline=host.is_offline(),
            cluster_nodes=host.cluster_nodes(),
        ),
    )


def serialize_host_collection(
    hosts: Iterable[Host],
    *,
    compute_effective_attributes: bool,
    compute_links: bool,
) -> HostConfigCollectionModel:
    return HostConfigCollectionModel(
        domainType="host_config",
        id="host",
        extensions=ApiOmitted(),
        value=[
            serialize_host(
                host=host,
                compute_links=compute_links,
                compute_effective_attributes=compute_effective_attributes,
            )
            for host in hosts
        ],
        links=[LinkModel.create("self", constructors.collection_href("host_config"))],
    )


def host_etag(host: Host) -> ETag:
    return ETag(
        {
            "name": host.name(),
            "attributes": {k: v for k, v in host.attributes.items() if k != "meta_data"},
            "cluster_nodes": host.cluster_nodes(),
        }
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


def bulk_host_action_response(
    failed_hosts: dict[HostName, str], succeeded_hosts: Iterable[Host]
) -> HostConfigCollectionModel:
    host_collection = serialize_host_collection(
        succeeded_hosts, compute_effective_attributes=False, compute_links=False
    )
    if failed_hosts:
        # we neet to serialize to a (JSON-like) dict, without the omitted fields
        success_bytes = json_dump_without_omitted(HostConfigCollectionModel, host_collection)
        success_dict = json.loads(success_bytes)
        raise ProblemException(
            status=400,
            title="Some actions failed",
            detail=f"Some of the actions were performed but the following were faulty and "
            f"were skipped: {', '.join(failed_hosts)}.",
            ext=EXT(
                {
                    "succeeded_hosts": success_dict,
                    "failed_hosts": failed_hosts,
                }
            ),
        )

    return host_collection
