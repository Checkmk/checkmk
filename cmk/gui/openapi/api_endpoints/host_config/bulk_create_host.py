#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import itertools
import json
from collections.abc import Iterable
from typing import Annotated

from cmk.ccc.hostaddress import HostName
from cmk.ccc.version import Edition
from cmk.gui.exceptions import MKAuthException, MKUserError
from cmk.gui.fields.utils import edition_field_description
from cmk.gui.logged_in import user
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
    json_dump_without_omitted,
)
from cmk.gui.openapi.framework.model.restrict_editions import RestrictEditions
from cmk.gui.openapi.restful_objects.constructors import domain_type_action_href
from cmk.gui.openapi.shared_endpoint_families.host_config import HOST_CONFIG_FAMILY
from cmk.gui.openapi.utils import EXT, ProblemException
from cmk.gui.watolib import bakery
from cmk.gui.watolib.hosts_and_folders import Folder, Host

from ._utils import PERMISSIONS_CREATE, serialize_host_collection
from .create_host import CreateHostModel
from .models.response_models import BulkHostActionWithFailedHostsModel, HostConfigCollectionModel


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


def _bulk_host_action_response(
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


def bulk_create_host_v1(
    api_context: ApiContext,
    body: BulkCreateHostModel,
    bake_agent: Annotated[
        bool | ApiOmitted,
        RestrictEditions(excluded_editions={Edition.CRE}),
        QueryParam(
            description=edition_field_description(
                "Tries to bake the agents for the just created hosts. This process is started in the "
                "background after configuring the host. Please note that the baking may take some "
                "time and might block subsequent API calls.",
                excluded_editions={Edition.CRE},
            ),
            example="True",
        ),
    ] = ApiOmitted(),
) -> HostConfigCollectionModel:
    """Bulk create hosts"""
    user.need_permission("wato.edit")
    failed_hosts: dict[HostName, str] = {}
    succeeded_hosts: list[HostName] = []

    for folder, grouped_hosts in itertools.groupby(
        sorted(body.entries, key=_folder_key), key=_folder_key
    ):
        validated_entries = []
        folder.prepare_create_hosts()
        for host in grouped_hosts:
            try:
                validated_entries.append(
                    (
                        host.host_name,
                        folder.verify_and_update_host_details(
                            host.host_name, host.attributes.to_internal()
                        ),
                        None,
                    )
                )
            except (MKUserError, MKAuthException) as e:
                failed_hosts[host.host_name] = f"Validation failed: {e}"

        folder.create_validated_hosts(
            validated_entries,
            pprint_value=api_context.config.wato_pprint_config,
            use_git=api_context.config.wato_use_git,
        )
        succeeded_hosts.extend(entry[0] for entry in validated_entries)

    if bake_agent:
        bakery.try_bake_agents_for_hosts(succeeded_hosts, debug=api_context.config.debug)

    return _bulk_host_action_response(
        failed_hosts, [Host.load_host(host_name) for host_name in succeeded_hosts]
    )


ENDPOINT_BULK_CREATE_HOST = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=domain_type_action_href("host_config", "bulk-create"),
        link_relation="cmk/bulk_create",
        method="post",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS_CREATE),
    doc=EndpointDoc(family=HOST_CONFIG_FAMILY.name),
    versions={
        APIVersion.UNSTABLE: EndpointHandler(
            handler=bulk_create_host_v1,
            error_schemas={400: BulkHostActionWithFailedHostsModel},
        )
    },
)
