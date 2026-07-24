#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import itertools
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
    QueryParam,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model import (
    api_field,
    api_model,
    ApiOmitted,
)
from cmk.gui.openapi.framework.model.restrict_features import RestrictFeatures
from cmk.gui.openapi.restful_objects.constructors import domain_type_action_href
from cmk.gui.utils import permission_verification as permissions
from cmk.gui.watolib import bakery
from cmk.gui.watolib.hosts_and_folders import Folder, make_folder_tree
from cmk.licensing.basics.options import OptionName

from ._family import HOST_CONFIG_FAMILY
from ._utils import (
    bulk_host_action_response,
    make_pending_changes,
    rw_permissions,
)
from .create_host import CreateHostModel
from .models.response_models import BulkHostActionWithFailedHostsModel, HostConfigCollectionModel

# Bulk create may be called with an empty entry list, in which case only ``wato.edit`` is
# exercised. ``wato.manage_hosts`` is therefore optional.
PERMISSIONS_BULK_CREATE = rw_permissions(
    permissions.Perm("wato.edit"),
    permissions.Optional(permissions.Perm("wato.manage_hosts")),
)


@api_model
class BulkCreateHostModel:
    entries: list[CreateHostModel] = api_field(
        description="A list of host entries.",
        example=[
            {
                "host_name": "example.com",
                "folder": "/",
                "attributes": {},
            }
        ],
    )


def _folder_key(host: CreateHostModel) -> Folder:
    """Key function to group hosts by folder."""
    return host.folder


def bulk_create_host_v1(
    api_context: ApiContext,
    body: BulkCreateHostModel,
    bake_agent: Annotated[
        bool | ApiOmitted,
        RestrictFeatures(option_name=OptionName.BAKERY, which_field="bake_agent"),
        QueryParam(
            description=(
                "Tries to bake the agents for the just created hosts. This process is started in the "
                "background after configuring the host. Please note that the baking may take some "
                "time and might block subsequent API calls. "
                "Requires the agent bakery feature to be licensed."
            ),
            example="True",
        ),
    ] = ApiOmitted(),
) -> HostConfigCollectionModel:
    """Bulk create hosts"""
    api_context.user.need_permission("wato.edit")
    acting_user = api_context.user
    failed_hosts: dict[HostName, str] = {}
    succeeded_hosts: list[HostName] = []

    for folder, grouped_hosts in itertools.groupby(
        sorted(body.entries, key=_folder_key), key=_folder_key
    ):
        validated_entries = []
        folder.prepare_create_hosts(acting_user=acting_user)
        for host in grouped_hosts:
            try:
                validated_entries.append(
                    (
                        host.host_name,
                        folder.verify_and_update_host_details(
                            host.host_name, host.attributes.to_internal(), acting_user=acting_user
                        ),
                        None,
                    )
                )
            except (MKUserError, MKAuthException) as e:
                failed_hosts[host.host_name] = f"Validation failed: {e}"

        folder.create_validated_hosts(
            validated_entries,
            pprint_value=api_context.config.wato_pprint_config,
            pending_changes=make_pending_changes(api_context),
            acting_user=acting_user,
        )
        succeeded_hosts.extend(entry[0] for entry in validated_entries)

    if not isinstance(bake_agent, ApiOmitted) and bake_agent:
        bakery.try_bake_agents_for_hosts(succeeded_hosts, debug=api_context.config.debug)

    return bulk_host_action_response(
        failed_hosts,
        [
            make_folder_tree(api_context.config).load_host(host_name)
            for host_name in succeeded_hosts
        ],
        api_context=api_context,
    )


ENDPOINT_BULK_CREATE_HOST = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=domain_type_action_href("host_config", "bulk-create"),
        link_relation="cmk/bulk_create",
        method="post",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS_BULK_CREATE),
    doc=EndpointDoc(family=HOST_CONFIG_FAMILY.name),
    versions={
        APIVersion.V1: EndpointHandler(
            handler=bulk_create_host_v1,
            error_schemas={400: BulkHostActionWithFailedHostsModel},
        )
    },
)
