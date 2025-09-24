#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import Annotated

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.gui.logged_in import user
from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.framework.model.converter import HostConverter, TypedPlainValidator
from cmk.gui.openapi.restful_objects.constructors import domain_type_action_href
from cmk.gui.openapi.shared_endpoint_families.host_config import HOST_CONFIG_FAMILY
from cmk.gui.watolib.hosts_and_folders import Folder, Host

from ._utils import (
    bulk_host_action_response,
    PERMISSIONS_UPDATE,
    validate_host_attributes_for_quick_setup,
)
from .models.request_models import UpdateHost
from .models.response_models import BulkHostActionWithFailedHostsModel, HostConfigCollectionModel


@api_model
class UpdateHostEntry(UpdateHost):
    host: Annotated[
        Host,
        TypedPlainValidator(str, HostConverter(permission_type="setup_write").host),
    ] = api_field(
        description="The hostname or IP address itself.",
        example="myhost.example.com",
        serialization_alias="host_name",
    )


@api_model
class BulkUpdateHostModel:
    entries: Sequence[UpdateHostEntry] = api_field(description="A list of host entries.")


def bulk_update_hosts_v1(
    api_context: ApiContext,
    body: BulkUpdateHostModel,
) -> HostConfigCollectionModel:
    """Bulk update hosts

    Please be aware that when doing bulk updates, it is not possible to prevent the
    [Updating Values]("lost update problem"), which is normally prevented by the ETag locking
    mechanism. Use at your own risk.
    """
    user.need_permission("wato.edit")
    user.need_permission("wato.edit_hosts")

    succeeded_hosts: list[Host] = []
    failed_hosts: dict[HostName, str] = {}

    hosts_by_folder: dict[Folder, list[Host]] = {}
    updates_by_host_name: dict[HostName, list[UpdateHostEntry]] = {}
    for update in body.entries:
        hosts_by_folder.setdefault(update.host.folder(), []).append(update.host)
        updates_by_host_name.setdefault(update.host.name(), []).append(update)

    for folder, hosts in hosts_by_folder.items():
        pending_changes: list[tuple[Host, str, list[SiteId]]] = []
        for host in hosts:
            for update in updates_by_host_name[host.name()]:
                if not validate_host_attributes_for_quick_setup(host, update):
                    failed_hosts[host.name()] = "Host is locked by Quick setup."
                    continue

                attributes = (
                    update.attributes.to_internal() if update.attributes else host.attributes.copy()
                )

                if update.update_attributes:
                    attributes.update(update.update_attributes.to_internal())

                faulty_attributes = set()
                if update.remove_attributes:
                    remove_attributes_as_set = set(update.remove_attributes)
                    valid_attributes_to_remove = remove_attributes_as_set & set(attributes)
                    faulty_attributes = remove_attributes_as_set - valid_attributes_to_remove
                    for valid_attribute in valid_attributes_to_remove:
                        # mypy expects literal keys for typed dicts
                        del attributes[valid_attribute]  # type: ignore[misc]

                diff, affected_sites = host.apply_edit(attributes, host.cluster_nodes())
                pending_changes.append((host, diff, affected_sites))

                if faulty_attributes:
                    failed_hosts[host.name()] = (
                        f"Failed to remove {', '.join(sorted(faulty_attributes))}"
                    )
                else:
                    succeeded_hosts.append(host)

        # skip save if no changes were made, presumably due to quick setup lock
        if pending_changes:
            folder.save_hosts(pprint_value=api_context.config.wato_pprint_config)
            for host, diff, affected_sites in pending_changes:
                host.add_edit_host_change(
                    diff, affected_sites, use_git=api_context.config.wato_use_git
                )

    return bulk_host_action_response(failed_hosts, succeeded_hosts)


ENDPOINT_BULK_UPDATE_HOST = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=domain_type_action_href("host_config", "bulk-update"),
        link_relation="cmk/bulk_update",
        method="put",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS_UPDATE),
    doc=EndpointDoc(family=HOST_CONFIG_FAMILY.name),
    versions={
        APIVersion.UNSTABLE: EndpointHandler(
            handler=bulk_update_hosts_v1,
            error_schemas={400: BulkHostActionWithFailedHostsModel},
        )
    },
)
