#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from http import HTTPStatus
from typing import Annotated

from cmk.ccc.hostaddress import HostName
from cmk.gui.exceptions import MKAuthException, MKUserError
from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model import api_field, api_model, ApiOmitted
from cmk.gui.openapi.framework.model.converter import HostConverter, TypedPlainValidator
from cmk.gui.openapi.restful_objects.constructors import domain_type_action_href
from cmk.gui.watolib.host_relations import with_links_not_shown
from cmk.gui.watolib.hosts_and_folders import (
    attributes_without,
    Folder,
    Host,
    HostEditResult,
    RelationMirrorBatch,
)

from ._family import HOST_CONFIG_FAMILY
from ._utils import (
    bulk_host_action_response,
    carry_over_unexposed_attributes,
    deprecated_attributes_error,
    make_pending_changes,
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
    api_context.user.need_permission("wato.edit")
    api_context.user.need_permission("wato.edit_hosts")
    acting_user = api_context.user

    succeeded_hosts: list[Host] = []
    failed_hosts: dict[HostName, str] = {}

    hosts_by_folder: dict[Folder, list[Host]] = {}
    updates_by_host_name: dict[HostName, list[UpdateHostEntry]] = {}
    for update in body.entries:
        hosts_by_folder.setdefault(update.host.folder(), []).append(update.host)
        updates_by_host_name.setdefault(update.host.name(), []).append(update)

    pending_changes = make_pending_changes(api_context)
    pprint_value = api_context.config.wato_pprint_config
    for folder, hosts in hosts_by_folder.items():
        edits: list[tuple[Host, HostEditResult]] = []
        mirror = RelationMirrorBatch(folder, acting_user=acting_user)
        for host in hosts:
            updates = updates_by_host_name[host.name()]

            requested: dict[str, object] = {}
            for update in updates:
                if update.attributes:
                    requested.update(update.attributes.to_internal())
                if update.update_attributes:
                    requested.update(update.update_attributes.to_internal())
            if (error := deprecated_attributes_error(host.attributes, requested)) is not None:
                failed_hosts[host.name()] = error
                continue

            stored_relations = host.attributes.get("relations", [])
            for update in updates:
                if not validate_host_attributes_for_quick_setup(host, update):
                    failed_hosts[host.name()] = "Host is locked by Quick setup."
                    continue

                attributes = (
                    carry_over_unexposed_attributes(
                        host.attributes, update.attributes.to_internal()
                    )
                    if update.attributes
                    else host.attributes.copy()
                )

                if update.update_attributes:
                    attributes.update(update.update_attributes.to_internal())

                faulty_attributes = set()
                if update.remove_attributes:
                    remove_attributes_as_set = set(update.remove_attributes)
                    valid_attributes_to_remove = remove_attributes_as_set & set(attributes)
                    faulty_attributes = remove_attributes_as_set - valid_attributes_to_remove
                    attributes = attributes_without(attributes, valid_attributes_to_remove)

                if _states_relations(update):
                    attributes["relations"] = with_links_not_shown(
                        attributes.get("relations", []), stored_relations
                    )

                try:
                    mirror.need_edit(host, attributes)
                except (MKUserError, MKAuthException) as e:
                    failed_hosts[host.name()] = f"Validation failed: {e}"
                    continue

                edits.append(
                    (
                        host,
                        host.apply_edit(attributes, host.cluster_nodes(), acting_user=acting_user),
                    )
                )
                # Written before the next host is edited, which may be one of the counterparts.
                mirror.write()

                if faulty_attributes:
                    failed_hosts[host.name()] = (
                        f"Failed to remove {', '.join(sorted(faulty_attributes))}"
                    )
                else:
                    succeeded_hosts.append(host)

        # skip save if no changes were made, presumably due to quick setup lock
        if edits:
            folder.save_hosts(pprint_value=pprint_value, acting_user=acting_user)
            for host, edit in edits:
                host.add_edit_host_change(edit, pending_changes=pending_changes)
        mirror.save(pprint_value=pprint_value, pending_changes=pending_changes)

    return bulk_host_action_response(failed_hosts, succeeded_hosts, api_context=api_context)


def _states_relations(update: UpdateHostEntry) -> bool:
    """Whether the entry sets the relations - a full replacement does by leaving them out."""
    if not isinstance(update.attributes, ApiOmitted):
        return True
    if not isinstance(update.update_attributes, ApiOmitted):
        return not isinstance(update.update_attributes.relations, ApiOmitted)
    return (
        not isinstance(update.remove_attributes, ApiOmitted)
        and "relations" in update.remove_attributes
    )


ENDPOINT_BULK_UPDATE_HOST = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=domain_type_action_href("host_config", "bulk-update"),
        link_relation="cmk/bulk_update",
        method="put",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS_UPDATE),
    doc=EndpointDoc(family=HOST_CONFIG_FAMILY.name),
    versions={
        APIVersion.V1: EndpointHandler(
            handler=bulk_update_hosts_v1,
            error_schemas={HTTPStatus.BAD_REQUEST: BulkHostActionWithFailedHostsModel},
        )
    },
)
