#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Hosts

A host is an object that is monitored by Checkmk, for example, a server or a network device.
A host belongs to a certain folder, is usually connected to a data source (agent or SNMP) and
provides one or more services.

A cluster host is a special host type containing the nodes the cluster consists of and having
the services assigned that are provided by the cluster.

You can find an introduction to hosts in the
[Checkmk guide](https://docs.checkmk.com/latest/en/wato_hosts.html).

Please note that every host always resides in a folder. The folder is included twice
in the host's links: Once based upon the canonical path and once based upon the folder's
unique id. You can never remove a host from a folder, just move it to a different one.

### Host and Folder attributes

Every host and folder can have "attributes" set, which determine the behavior of Checkmk. Each
host inherits all attributes of its folder and the folder's parent folders. So setting an SNMP
community in a folder is equivalent to setting the same on all hosts in said folder.

Some host endpoints allow one to view the "effective attributes", which is an aggregation of all
attributes up to the root.

### Relations

A host_config object can have the following relations present in `links`:

 * `self` - The host itself.
 * `urn:com.checkmk:rels/folder_config` - The folder object this host resides in.
 * `urn:org.restfulobjects:rels/update` - The endpoint to update this host.
 * `urn:org.restfulobjects:rels/delete` - The endpoint to delete this host.

"""

import itertools
import operator
from collections.abc import Callable, Iterable, Mapping, Sequence
from functools import partial
from typing import Any
from urllib.parse import urlparse

from cmk.utils.global_ident_type import is_locked_by_quick_setup
from cmk.utils.hostaddress import HostName

from cmk.gui import fields as gui_fields
from cmk.gui.background_job import InitialStatusArgs
from cmk.gui.exceptions import MKAuthException, MKUserError
from cmk.gui.fields.utils import BaseSchema
from cmk.gui.http import request, Response
from cmk.gui.logged_in import user
from cmk.gui.openapi.endpoints.common_fields import field_include_extensions, field_include_links
from cmk.gui.openapi.endpoints.host_config.request_schemas import (
    BulkCreateHost,
    BulkDeleteHost,
    BulkUpdateHost,
    CreateClusterHost,
    CreateHost,
    MoveHost,
    RenameHost,
    UpdateHost,
    UpdateNodes,
)
from cmk.gui.openapi.endpoints.host_config.response_schemas import (
    HostConfigCollection,
    HostConfigSchema,
)
from cmk.gui.openapi.endpoints.utils import folder_slug
from cmk.gui.openapi.restful_objects import constructors, Endpoint, response_schemas
from cmk.gui.openapi.restful_objects.api_error import ApiError
from cmk.gui.openapi.restful_objects.parameters import HOST_NAME
from cmk.gui.openapi.restful_objects.registry import EndpointRegistry
from cmk.gui.openapi.restful_objects.type_defs import DomainObject, LinkType
from cmk.gui.openapi.utils import EXT, problem, serve_json
from cmk.gui.utils import permission_verification as permissions
from cmk.gui.wato.pages.host_rename import rename_hosts_background_job
from cmk.gui.watolib import bakery
from cmk.gui.watolib.activate_changes import has_pending_changes
from cmk.gui.watolib.check_mk_automations import delete_hosts
from cmk.gui.watolib.host_attributes import HostAttributes
from cmk.gui.watolib.host_rename import RenameHostBackgroundJob, RenameHostsBackgroundJob
from cmk.gui.watolib.hosts_and_folders import Folder, folder_tree, Host

from cmk import fields

BAKE_AGENT_PARAM_NAME = "bake_agent"
BAKE_AGENT_PARAM = {
    BAKE_AGENT_PARAM_NAME: fields.Boolean(
        load_default=False,
        required=False,
        example=False,
        description=(
            "Tries to bake the agents for the just created hosts. This process is started in the "
            "background after configuring the host. Please note that the backing may take some "
            "time and might block subsequent API calls. "
            "This only works when using the Enterprise Editions."
        ),
    )
}

EFFECTIVE_ATTRIBUTES = {
    "effective_attributes": fields.Boolean(
        load_default=False,
        required=False,
        example=False,
        description=(
            "Show all effective attributes on hosts, not just the attributes which were set on "
            "this host specifically. This includes all attributes of all of this host's parent "
            "folders."
        ),
    )
}

PERMISSIONS = permissions.AllPerm(
    [
        permissions.Perm("wato.edit"),
        permissions.Perm("wato.manage_hosts"),
        permissions.Optional(permissions.Perm("wato.all_folders")),
        permissions.Undocumented(
            permissions.AnyPerm(
                [
                    permissions.OkayToIgnorePerm("bi.see_all"),
                    permissions.Perm("general.see_all"),
                    permissions.OkayToIgnorePerm("mkeventd.seeall"),
                ]
            )
        ),
    ]
)

BULK_CREATE_PERMISSIONS = permissions.AllPerm(
    [
        permissions.Perm("wato.edit"),
        permissions.Optional(permissions.Perm("wato.manage_hosts")),
        permissions.Optional(permissions.Perm("wato.all_folders")),
        permissions.Undocumented(
            permissions.AnyPerm(
                [
                    permissions.OkayToIgnorePerm("bi.see_all"),
                    permissions.Perm("general.see_all"),
                    permissions.OkayToIgnorePerm("mkeventd.seeall"),
                ]
            )
        ),
    ]
)

UPDATE_PERMISSIONS = permissions.AllPerm(
    [
        permissions.Perm("wato.edit"),
        permissions.Perm("wato.edit_hosts"),
        permissions.Optional(permissions.Perm("wato.all_folders")),
        permissions.Undocumented(
            permissions.AnyPerm(
                [
                    permissions.OkayToIgnorePerm("bi.see_all"),
                    permissions.Perm("general.see_all"),
                    permissions.OkayToIgnorePerm("mkeventd.seeall"),
                    # only used to check if user can see a host
                    permissions.Perm("wato.see_all_folders"),
                ]
            )
        ),
    ]
)


def with_access_check_permission(perm: permissions.BasePerm) -> permissions.BasePerm:
    """To check if a user can see a host, we currently need the 'wato.see_all_folders' permission.
    Since this use is done internally only, we want to add it without documenting it."""
    return permissions.AllPerm(
        [
            perm,
            permissions.Undocumented(
                permissions.AnyPerm(
                    [
                        permissions.OkayToIgnorePerm("bi.see_all"),
                        permissions.Perm("general.see_all"),
                        permissions.OkayToIgnorePerm("mkeventd.seeall"),
                        # is only used to check if a user can see a host
                        permissions.Perm("wato.see_all_folders"),
                    ],
                )
            ),
        ]
    )


@Endpoint(
    constructors.collection_href("host_config"),
    "cmk/create",
    method="post",
    etag="output",
    request_schema=CreateHost,
    response_schema=HostConfigSchema,
    query_params=[BAKE_AGENT_PARAM],
    permissions_required=PERMISSIONS,
)
def create_host(params: Mapping[str, Any]) -> Response:
    """Create a host"""
    user.need_permission("wato.edit")
    body = params["body"]
    host_name: HostName = body["host_name"]
    folder: Folder = body["folder"]

    # is_cluster is defined as "cluster_hosts is not None"
    folder.create_hosts(
        [(host_name, body["attributes"], None)],
    )
    if params[BAKE_AGENT_PARAM_NAME]:
        bakery.try_bake_agents_for_hosts([host_name])

    host = Host.load_host(host_name)
    return _serve_host(host, False)


@Endpoint(
    constructors.collection_href("host_config", "clusters"),
    "cmk/create_cluster",
    method="post",
    etag="output",
    request_schema=CreateClusterHost,
    response_schema=HostConfigSchema,
    permissions_required=with_access_check_permission(PERMISSIONS),
    query_params=[BAKE_AGENT_PARAM],
)
def create_cluster_host(params: Mapping[str, Any]) -> Response:
    """Create a cluster host

    A cluster host groups many hosts (called nodes in this context) into a conceptual cluster.
    All the services of the individual nodes will be collated on the cluster host."""
    user.need_permission("wato.edit")
    body = params["body"]
    host_name: HostName = body["host_name"]
    folder: Folder = body["folder"]

    folder.create_hosts(
        [(host_name, body["attributes"], body["nodes"])],
    )
    if params[BAKE_AGENT_PARAM_NAME]:
        bakery.try_bake_agents_for_hosts([host_name])

    host = Host.load_host(host_name)
    return _serve_host(host, effective_attributes=False)


class FailedHosts(BaseSchema):
    succeeded_hosts = fields.Nested(
        HostConfigCollection,
        description="The list of succeeded host objects",
    )
    failed_hosts = fields.Dict(
        keys=fields.String(description="Name of the host"),
        values=fields.String(description="The error message"),
        description="Detailed error messages on hosts failing the action",
    )


class BulkHostActionWithFailedHosts(ApiError):
    title = fields.String(
        description="A summary of the problem.",
        example="Some actions failed",
    )
    status = fields.Integer(
        description="The HTTP status code.",
        example=400,
    )
    detail = fields.String(
        description="Detailed information on what exactly went wrong.",
        example="Some of the actions were performed but the following were faulty and were skipped: ['host1', 'host2'].",
    )
    ext = fields.Nested(
        FailedHosts,
        description="Details for which hosts have failed",
    )


@Endpoint(
    constructors.domain_type_action_href("host_config", "bulk-create"),
    "cmk/bulk_create",
    method="post",
    request_schema=BulkCreateHost,
    response_schema=HostConfigCollection,
    error_schemas={
        400: BulkHostActionWithFailedHosts,
    },
    permissions_required=BULK_CREATE_PERMISSIONS,
    query_params=[BAKE_AGENT_PARAM],
)
def bulk_create_hosts(params: Mapping[str, Any]) -> Response:
    """Bulk create hosts"""
    user.need_permission("wato.edit")
    body = params["body"]
    entries = body["entries"]

    failed_hosts: dict[HostName, str] = {}
    succeeded_hosts: list[HostName] = []
    folder: Folder
    for folder, grouped_hosts in itertools.groupby(entries, operator.itemgetter("folder")):
        validated_entries = []
        folder.prepare_create_hosts()
        for host in grouped_hosts:
            host_name = host["host_name"]
            try:
                validated_entries.append(
                    (
                        host_name,
                        folder.verify_and_update_host_details(host_name, host["attributes"]),
                        None,
                    )
                )
            except (MKUserError, MKAuthException) as e:
                failed_hosts[host_name] = f"Validation failed: {e}"

        folder.create_validated_hosts(validated_entries)
        succeeded_hosts.extend(entry[0] for entry in validated_entries)

    if params[BAKE_AGENT_PARAM_NAME]:
        bakery.try_bake_agents_for_hosts(succeeded_hosts)

    return _bulk_host_action_response(
        failed_hosts, [Host.load_host(host_name) for host_name in succeeded_hosts]
    )


def _bulk_host_action_response(
    failed_hosts: dict[HostName, str], succeeded_hosts: Sequence[Host]
) -> Response:
    if failed_hosts:
        return problem(
            status=400,
            title="Some actions failed",
            detail=f"Some of the actions were performed but the following were faulty and "
            f"were skipped: {' ,'.join(failed_hosts)}.",
            ext=EXT(
                {
                    "succeeded_hosts": _host_collection(succeeded_hosts),
                    "failed_hosts": failed_hosts,
                }
            ),
        )

    return serve_host_collection(succeeded_hosts)


@Endpoint(
    constructors.collection_href("host_config"),
    ".../collection",
    method="get",
    response_schema=HostConfigCollection,
    permissions_required=permissions.Optional(permissions.Perm("wato.see_all_folders")),
    query_params=[
        EFFECTIVE_ATTRIBUTES,
        field_include_links(
            "Flag which toggles whether the links field of the individual hosts should be populated."
        ),
        field_include_extensions(),
    ],
)
def list_hosts(params: Mapping[str, Any]) -> Response:
    """Show all hosts"""
    root_folder = folder_tree().root_folder()
    hosts = (
        host
        for host in root_folder.all_hosts_recursively().values()
        if host.permissions.may("read")
    )
    return serve_host_collection(
        hosts,
        effective_attributes=params["effective_attributes"],
        include_links=params["include_links"],
        include_extensions=params["include_extensions"],
    )


def serve_host_collection(
    hosts: Iterable[Host],
    *,
    effective_attributes: bool = False,
    include_links: bool = False,
    include_extensions: bool = True,
) -> Response:
    return serve_json(
        _host_collection(
            hosts,
            effective_attributes=effective_attributes,
            include_links=include_links,
            include_extensions=include_extensions,
        )
    )


def _host_collection(
    hosts: Iterable[Host],
    *,
    effective_attributes: bool = False,
    include_links: bool = False,
    include_extensions: bool = True,
) -> dict[str, Any]:
    return {
        "id": "host",
        "domainType": "host_config",
        "value": [
            serialize_host(
                host,
                effective_attributes=effective_attributes,
                include_links=include_links,
                include_extensions=include_extensions,
            )
            for host in hosts
        ],
        "links": [constructors.link_rel("self", constructors.collection_href("host_config"))],
    }


@Endpoint(
    constructors.object_property_href("host_config", "{host_name}", "nodes"),
    ".../property",
    method="put",
    path_params=[
        {
            "host_name": gui_fields.HostField(
                description="A cluster host.",
                should_be_cluster=True,
            ),
        }
    ],
    etag="both",
    request_schema=UpdateNodes,
    response_schema=response_schemas.ObjectProperty,
    permissions_required=UPDATE_PERMISSIONS,
)
def update_nodes(params: Mapping[str, Any]) -> Response:
    """Update the nodes of a cluster host"""
    user.need_permission("wato.edit")
    user.need_permission("wato.edit_hosts")
    host_name = params["host_name"]
    body = params["body"]
    nodes = body["nodes"]
    host: Host = Host.load_host(host_name)
    _require_host_etag(host)
    host.edit(host.attributes, nodes)

    return serve_json(
        constructors.object_sub_property(
            domain_type="host_config",
            ident=host_name,
            name="nodes",
            value=host.cluster_nodes(),
        )
    )


def _validate_host_attributes_for_quick_setup(host: Host, body: dict[str, Any]) -> bool:
    if not is_locked_by_quick_setup(host.locked_by()):
        return True

    locked_attributes: Sequence[str] = host.attributes.get("locked_attributes", [])
    new_attributes: HostAttributes | None = body.get("attributes")
    update_attributes: HostAttributes | None = body.get("update_attributes")
    remove_attributes: Sequence[str] | None = body.get("remove_attributes")

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


@Endpoint(
    constructors.object_href("host_config", "{host_name}"),
    ".../update",
    method="put",
    path_params=[HOST_NAME],
    etag="both",
    request_schema=UpdateHost,
    response_schema=HostConfigSchema,
    permissions_required=UPDATE_PERMISSIONS,
)
def update_host(params: Mapping[str, Any]) -> Response:
    """Update a host"""
    user.need_permission("wato.edit")
    user.need_permission("wato.edit_hosts")
    host: Host = Host.load_host(params["host_name"])
    _require_host_etag(host)
    body = params["body"]

    if not _validate_host_attributes_for_quick_setup(host, body):
        return problem(
            status=400,
            title=f'The host "{host.name()}" is locked by Quick setup.',
            detail="Cannot modify locked attributes.",
        )

    if new_attributes := body.get("attributes"):
        new_attributes["meta_data"] = host.attributes.get("meta_data", {})
        host.edit(new_attributes, None)

    if update_attributes := body.get("update_attributes"):
        host.update_attributes(update_attributes)

    if remove_attributes := body.get("remove_attributes"):
        faulty_attributes = []
        for attribute in remove_attributes:
            if attribute not in host.attributes:
                faulty_attributes.append(attribute)

        host.clean_attributes(remove_attributes)  # silently ignores missing attributes

        if faulty_attributes:
            return problem(
                status=400,
                title="Some attributes were not removed",
                detail=f"The following attributes were not removed since they didn't exist: {', '.join(faulty_attributes)}",
            )

    return _serve_host(host, effective_attributes=False)


@Endpoint(
    constructors.domain_type_action_href("host_config", "bulk-update"),
    "cmk/bulk_update",
    method="put",
    request_schema=BulkUpdateHost,
    response_schema=HostConfigCollection,
    error_schemas={
        400: BulkHostActionWithFailedHosts,
    },
    permissions_required=UPDATE_PERMISSIONS,
)
def bulk_update_hosts(params: Mapping[str, Any]) -> Response:
    """Bulk update hosts

    Please be aware that when doing bulk updates, it is not possible to prevent the
    [Updating Values]("lost update problem"), which is normally prevented by the ETag locking
    mechanism. Use at your own risk.
    """
    user.need_permission("wato.edit")
    user.need_permission("wato.edit_hosts")
    body = params["body"]

    succeeded_hosts: list[Host] = []
    failed_hosts: dict[HostName, str] = {}

    for update_detail in body["entries"]:
        host_name = update_detail["host_name"]
        host: Host = Host.load_host(host_name)

        if not _validate_host_attributes_for_quick_setup(host, update_detail):
            failed_hosts[host_name] = "Host is locked by Quick setup."

        faulty_attributes = []

        if new_attributes := update_detail.get("attributes"):
            host.edit(new_attributes, None)

        if update_attributes := update_detail.get("update_attributes"):
            host.update_attributes(update_attributes)

        if remove_attributes := update_detail.get("remove_attributes"):
            for attribute in remove_attributes:
                if attribute not in host.attributes:
                    faulty_attributes.append(attribute)

            host.clean_attributes(remove_attributes)

        if faulty_attributes:
            failed_hosts[host_name] = f"Failed to remove {', '.join(faulty_attributes)}"
            continue

        succeeded_hosts.append(host)

    return _bulk_host_action_response(failed_hosts, succeeded_hosts)


@Endpoint(
    constructors.object_action_href("host_config", "{host_name}", action_name="rename"),
    "cmk/rename",
    method="put",
    path_params=[
        {
            "host_name": gui_fields.HostField(
                description="A host name.",
                should_exist=True,
                permission_type="setup_write",
            ),
        }
    ],
    etag="both",
    additional_status_codes=[303, 409, 422],
    status_descriptions={
        303: "The host rename process is still running. Redirecting to the 'Wait for completion' endpoint",
        409: "There are pending changes not yet activated or a rename background job is already running.",
        422: "The host could not be renamed.",
    },
    permissions_required=permissions.AllPerm(
        [
            permissions.Perm("wato.all_folders"),
            permissions.Perm("wato.edit_hosts"),
            permissions.Perm("wato.rename_hosts"),
            permissions.Perm("wato.see_all_folders"),
        ]
    ),
    request_schema=RenameHost,
    response_schema=HostConfigSchema,
)
def rename_host(params: Mapping[str, Any]) -> Response:
    """Rename a host

    This endpoint will start a background job to rename the host. Only one rename background job
    can run at a time.
    """
    user.need_permission("wato.edit_hosts")
    user.need_permission("wato.rename_hosts")
    if has_pending_changes():
        return problem(
            status=409,
            title="Pending changes are present",
            detail="Please activate all pending changes before executing a host rename process",
        )
    host_name = HostName(params["host_name"])
    host: Host = Host.load_host(host_name)
    new_name = HostName(params["body"]["new_name"])

    if is_locked_by_quick_setup(host.locked_by()):
        return problem(
            status=400,
            title=f'The host "{host_name}" is locked by Quick setup.',
            detail="Locked hosts cannot be renamed.",
        )

    background_job = RenameHostBackgroundJob(host)
    result = background_job.start(
        partial(rename_hosts_background_job, [(host.folder().path(), host_name, new_name)]),
        InitialStatusArgs(
            title="Renaming of %s -> %s" % (host_name, new_name),
            lock_wato=True,
            stoppable=False,
            estimated_duration=background_job.get_status().duration,
            user=str(user.id) if user.id else None,
        ),
    )
    if result.is_error():
        return problem(status=409, title="Conflict", detail=result.error)

    response = Response(status=303)
    response.location = urlparse(
        constructors.link_endpoint(
            "cmk.gui.openapi.endpoints.host_config",
            "cmk/wait-for-completion",
            parameters={},
        )["href"]
    ).path
    return response


@Endpoint(
    constructors.domain_type_action_href("host_config", "wait-for-completion"),
    "cmk/wait-for-completion",
    method="get",
    status_descriptions={
        204: "The renaming job has been completed.",
        302: (
            "The renaming job is still running. Redirecting to the "
            "'Wait for completion' endpoint."
        ),
        404: "There is no running renaming job",
    },
    additional_status_codes=[302, 404],
    output_empty=True,
)
def renaming_job_wait_for_completion(params: Mapping[str, Any]) -> Response:
    """Wait for renaming process completion

    This endpoint will redirect on itself to prevent timeouts.
    """
    job_exists, job_is_active = RenameHostsBackgroundJob.status_checks()
    if not job_exists:
        return problem(
            status=404,
            title="Not found",
            detail="No running renaming job was found",
        )

    if job_is_active:
        response = Response(status=302)
        response.location = urlparse(request.url).path
        return response
    return Response(status=204)


@Endpoint(
    constructors.object_action_href("host_config", "{host_name}", action_name="move"),
    "cmk/move",
    method="post",
    path_params=[HOST_NAME],
    etag="both",
    additional_status_codes=[403],
    request_schema=MoveHost,
    response_schema=HostConfigSchema,
    permissions_required=permissions.AllPerm(
        [
            permissions.Perm("wato.edit"),
            permissions.Perm("wato.edit_hosts"),
            permissions.Perm("wato.move_hosts"),
            permissions.Undocumented(permissions.Perm("wato.see_all_folders")),
            *PERMISSIONS.perms,
        ]
    ),
)
def move(params: Mapping[str, Any]) -> Response:
    """Move a host to another folder"""
    user.need_permission("wato.edit")
    user.need_permission("wato.move_hosts")
    host_name = params["host_name"]
    host: Host = Host.load_host(host_name)
    _require_host_etag(host)
    current_folder = host.folder()
    target_folder: Folder = params["body"]["target_folder"]

    if target_folder is current_folder:
        return problem(
            status=400,
            title="Invalid move action",
            detail="The host is already part of the specified target folder",
        )
    try:
        if target_folder.as_choice_for_moving() not in current_folder.choices_for_moving_host():
            raise MKAuthException
        current_folder.move_hosts([host_name], target_folder)
    except MKAuthException:
        return problem(
            status=403,
            title="Permission denied",
            detail=f"You lack the permissions to move host {host.name()} to {folder_slug(target_folder)}.",
        )
    return _serve_host(host, effective_attributes=False)


@Endpoint(
    constructors.object_href("host_config", "{host_name}"),
    ".../delete",
    method="delete",
    path_params=[HOST_NAME],
    output_empty=True,
    permissions_required=with_access_check_permission(PERMISSIONS),
)
def delete(params: Mapping[str, Any]) -> Response:
    """Delete a host"""
    user.need_permission("wato.edit")
    host: Host = Host.load_host(params["host_name"])
    host.folder().delete_hosts([host.name()], automation=delete_hosts)
    return Response(status=204)


@Endpoint(
    constructors.domain_type_action_href("host_config", "bulk-delete"),
    ".../delete",
    method="post",
    request_schema=BulkDeleteHost,
    permissions_required=with_access_check_permission(PERMISSIONS),
    output_empty=True,
)
def bulk_delete(params: Mapping[str, Any]) -> Response:
    """Bulk delete hosts"""
    user.need_permission("wato.edit")
    body = params["body"]
    hostnames = body["entries"]

    # Ideally, we would not need folder id's. However, folders cannot be sorted.
    folder_by_id = {}
    folder_id_by_hostname = {}
    for hostname in hostnames:
        folder = Host.load_host(hostname).folder()
        folder_id_by_hostname[hostname] = folder.id()
        folder_by_id[folder.id()] = folder

    for id_, hostnames_per_folder in itertools.groupby(
        sorted(hostnames, key=folder_id_by_hostname.__getitem__),
        key=folder_id_by_hostname.__getitem__,
    ):
        folder = folder_by_id[id_]
        # Calling Folder.delete_hosts is very expensive. Thus, we only call it once per folder.
        folder.delete_hosts(list(hostnames_per_folder), automation=delete_hosts)

    return Response(status=204)


@Endpoint(
    constructors.object_href("host_config", "{host_name}"),
    "cmk/show",
    method="get",
    path_params=[
        {
            "host_name": gui_fields.HostField(
                description="A host name.",
                should_exist=True,
                permission_type="setup_read",
            )
        }
    ],
    query_params=[EFFECTIVE_ATTRIBUTES],
    etag="output",
    response_schema=HostConfigSchema,
    permissions_required=permissions.Optional(permissions.Perm("wato.see_all_folders")),
)
def show_host(params: Mapping[str, Any]) -> Response:
    """Show a host"""
    host_name = params["host_name"]
    host: Host = Host.load_host(host_name)
    return _serve_host(host, effective_attributes=params["effective_attributes"])


def _serve_host(host: Host, effective_attributes: bool = False) -> Response:
    response = serve_json(serialize_host(host, effective_attributes=effective_attributes))
    return constructors.response_with_etag_created_from_dict(response, _host_etag_values(host))


agent_links_hook: Callable[[HostName], list[LinkType]] = lambda h: []


def serialize_host(
    host: Host,
    *,
    effective_attributes: bool,
    include_links: bool = True,
    include_extensions: bool = True,
) -> DomainObject:
    extensions = (
        {
            "folder": "/" + host.folder().path(),
            "attributes": host.attributes,
            "effective_attributes": host.effective_attributes() if effective_attributes else None,
            "is_cluster": host.is_cluster(),
            "is_offline": host.is_offline(),
            "cluster_nodes": host.cluster_nodes(),
        }
        if include_extensions
        else None
    )

    if include_links:
        links = [
            constructors.link_rel(
                rel="cmk/folder_config",
                href=constructors.object_href("folder_config", folder_slug(host.folder())),
                method="get",
                title="The folder config of the host.",
            ),
        ] + agent_links_hook(host.name())
    else:
        links = []

    return constructors.domain_object(
        domain_type="host_config",
        identifier=host.id(),
        title=host.alias() or host.name(),
        links=links,
        extensions=extensions,
        include_links=include_links,
    )


def _require_host_etag(host: Host) -> None:
    etag_values = _host_etag_values(host)
    constructors.require_etag(
        constructors.hash_of_dict(etag_values),
        error_details=EXT(etag_values),
    )


def _host_etag_values(host: Host) -> dict[str, Any]:
    # FIXME: Through some not yet fully explored effect, we do not get the actual persisted
    #        timestamp in the meta_data section but rather some other timestamp. This makes the
    #        reported ETag a different one than the one which is accepted by the endpoint.
    return {
        "name": host.name(),
        "attributes": {k: v for k, v in host.attributes.items() if k != "meta_data"},
        "cluster_nodes": host.cluster_nodes(),
    }


def register(endpoint_registry: EndpointRegistry) -> None:
    endpoint_registry.register(create_host)
    endpoint_registry.register(create_cluster_host)
    endpoint_registry.register(bulk_create_hosts)
    endpoint_registry.register(list_hosts)
    endpoint_registry.register(update_nodes)
    endpoint_registry.register(update_host)
    endpoint_registry.register(bulk_update_hosts)
    endpoint_registry.register(rename_host)
    endpoint_registry.register(renaming_job_wait_for_completion)
    endpoint_registry.register(move)
    endpoint_registry.register(delete)
    endpoint_registry.register(bulk_delete)
    endpoint_registry.register(show_host)
