#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
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
import json
import operator
from typing import Any, Dict, Iterable, List, Sequence
from urllib.parse import urlencode

import cmk.utils.version as cmk_version
from cmk.utils.type_defs import HostName

import cmk.gui.watolib.activate_changes as activate_changes
import cmk.gui.watolib.bakery as bakery
from cmk.gui import fields as gui_fields
from cmk.gui import watolib
from cmk.gui.exceptions import MKAuthException, MKUserError
from cmk.gui.fields.utils import BaseSchema
from cmk.gui.http import Response
from cmk.gui.logged_in import user
from cmk.gui.plugins.openapi.endpoints.utils import folder_slug
from cmk.gui.plugins.openapi.restful_objects import (
    constructors,
    Endpoint,
    permissions,
    request_schemas,
    response_schemas,
)
from cmk.gui.plugins.openapi.restful_objects.parameters import HOST_NAME
from cmk.gui.plugins.openapi.utils import problem
from cmk.gui.plugins.webapi.utils import check_hostname
from cmk.gui.watolib.host_rename import perform_rename_hosts
from cmk.gui.watolib.hosts_and_folders import CREFolder

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


PERMISSIONS = permissions.AllPerm(
    [
        permissions.Perm("wato.manage_hosts"),
        permissions.Optional(permissions.Perm("wato.all_folders")),
    ]
)


@Endpoint(
    constructors.collection_href("host_config"),
    "cmk/create",
    method="post",
    etag="output",
    request_schema=request_schemas.CreateHost,
    response_schema=response_schemas.HostConfigSchema,
    query_params=[BAKE_AGENT_PARAM],
    permissions_required=PERMISSIONS,
)
def create_host(params):
    """Create a host"""
    body = params["body"]
    host_name = body["host_name"]
    folder: CREFolder = body["folder"]

    # is_cluster is defined as "cluster_hosts is not None"
    folder.create_hosts(
        [(host_name, body["attributes"], None)], bake_hosts=params[BAKE_AGENT_PARAM_NAME]
    )

    host = watolib.Host.load_host(host_name)
    return _serve_host(host, False)


@Endpoint(
    constructors.collection_href("host_config", "clusters"),
    "cmk/create_cluster",
    method="post",
    etag="output",
    request_schema=request_schemas.CreateClusterHost,
    response_schema=response_schemas.HostConfigSchema,
    permissions_required=PERMISSIONS,
    query_params=[BAKE_AGENT_PARAM],
)
def create_cluster_host(params):
    """Create a cluster host

    A cluster host groups many hosts (called nodes in this context) into a conceptual cluster.
    All the services of the individual nodes will be collated on the cluster host."""
    body = params["body"]
    host_name = body["host_name"]
    folder: CREFolder = body["folder"]

    folder.create_hosts(
        [(host_name, body["attributes"], body["nodes"])], bake_hosts=params[BAKE_AGENT_PARAM_NAME]
    )

    host = watolib.Host.load_host(host_name)
    return _serve_host(host, effective_attributes=False)


class FailedHosts(BaseSchema):
    succeeded_hosts = fields.Nested(
        response_schemas.HostConfigCollection(),
        description="The list of succeeded host objects",
    )
    failed_hosts = fields.Dict(
        keys=fields.String(description="Name of the host"),
        values=fields.List(fields.String(description="The error messages")),
        description="Detailed error messages on hosts failing the action",
    )


class BulkHostActionWithFailedHosts(response_schemas.ApiError):
    ext = fields.Nested(
        FailedHosts,
        description="Details for which hosts have failed",
    )


@Endpoint(
    constructors.domain_type_action_href("host_config", "bulk-create"),
    "cmk/bulk_create",
    method="post",
    request_schema=request_schemas.BulkCreateHost,
    response_schema=response_schemas.HostConfigCollection,
    error_schemas={
        400: BulkHostActionWithFailedHosts,
    },
    permissions_required=PERMISSIONS,
    query_params=[BAKE_AGENT_PARAM],
)
def bulk_create_hosts(params):
    """Bulk create hosts"""
    body = params["body"]
    entries = body["entries"]

    failed_hosts: Dict[HostName, str] = {}
    succeeded_hosts: List[HostName] = []
    folder: CREFolder
    for folder, grouped_hosts in itertools.groupby(entries, operator.itemgetter("folder")):
        validated_entries = []
        folder.prepare_create_hosts()
        for host in grouped_hosts:
            host_name = host["host_name"]
            attributes = host["attributes"]
            try:
                folder.verify_host_details(host_name, attributes)
                validated_entries.append((host_name, attributes, None))
            except (MKUserError, MKAuthException) as e:
                failed_hosts[host_name] = f"Validation failed: {e}"

        folder.create_validated_hosts(validated_entries, bake_hosts=False)
        succeeded_hosts.extend(entry[0] for entry in validated_entries)

    if params[BAKE_AGENT_PARAM_NAME]:
        bakery.try_bake_agents_for_hosts(succeeded_hosts)

    return _bulk_host_action_response(
        failed_hosts, [watolib.Host.load_host(host_name) for host_name in succeeded_hosts]
    )


def _bulk_host_action_response(
    failed_hosts: Dict[HostName, str], succeeded_hosts: Sequence[watolib.CREHost]
) -> Response:
    if failed_hosts:
        return problem(
            status=400,
            title="Some actions failed",
            detail=f"Some of the actions were performed but the following were faulty and "
            f"were skipped: {' ,'.join(failed_hosts)}.",
            ext={
                "succeeded_hosts": _host_collection(succeeded_hosts),
                "failed_hosts": failed_hosts,
            },
        )

    return serve_host_collection(succeeded_hosts)


@Endpoint(
    constructors.collection_href("host_config"),
    ".../collection",
    method="get",
    response_schema=response_schemas.HostConfigCollection,
    permissions_required=permissions.Optional(permissions.Perm("wato.see_all_folders")),
)
def list_hosts(param) -> Response:
    """Show all hosts"""
    root_folder = watolib.Folder.root_folder()
    root_folder.need_recursive_permission("read")
    return serve_host_collection(root_folder.all_hosts_recursively().values())


def serve_host_collection(hosts: Iterable[watolib.CREHost]) -> Response:
    return constructors.serve_json(_host_collection(hosts))


def _host_collection(hosts: Iterable[watolib.CREHost]) -> dict[str, Any]:
    return {
        "id": "host",
        "domainType": "host_config",
        "value": [serialize_host(host, effective_attributes=False) for host in hosts],
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
    request_schema=request_schemas.UpdateNodes,
    response_schema=response_schemas.ObjectProperty,
    permissions_required=permissions.Perm("wato.all_folders"),
)
def update_nodes(params):
    """Update the nodes of a cluster host"""
    host_name = params["host_name"]
    body = params["body"]
    nodes = body["nodes"]
    host: watolib.CREHost = watolib.Host.load_host(host_name)
    _require_host_etag(host)
    host.edit(host.attributes(), nodes)

    return constructors.serve_json(
        constructors.object_sub_property(
            domain_type="host_config",
            ident=host_name,
            name="nodes",
            value=host.cluster_nodes(),
        )
    )


@Endpoint(
    constructors.object_href("host_config", "{host_name}"),
    ".../update",
    method="put",
    path_params=[HOST_NAME],
    etag="both",
    request_schema=request_schemas.UpdateHost,
    response_schema=response_schemas.HostConfigSchema,
    permissions_required=permissions.Perm("wato.all_folders"),
)
def update_host(params):
    """Update a host"""
    host_name = params["host_name"]
    body = params["body"]
    new_attributes = body["attributes"]
    update_attributes = body["update_attributes"]
    remove_attributes = body["remove_attributes"]
    check_hostname(host_name, should_exist=True)
    host: watolib.CREHost = watolib.Host.load_host(host_name)
    _require_host_etag(host)

    if new_attributes:
        host.edit(new_attributes, None)

    if update_attributes:
        host.update_attributes(update_attributes)

    faulty_attributes = []
    for attribute in remove_attributes:
        if not host.has_explicit_attribute(attribute):
            faulty_attributes.append(attribute)

    if remove_attributes:
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
    request_schema=request_schemas.BulkUpdateHost,
    response_schema=response_schemas.HostConfigCollection,
    error_schemas={
        400: BulkHostActionWithFailedHosts,
    },
    permissions_required=permissions.Perm("wato.all_folders"),
)
def bulk_update_hosts(params):
    """Bulk update hosts

    Please be aware that when doing bulk updates, it is not possible to prevent the
    [Updating Values]("lost update problem"), which is normally prevented by the ETag locking
    mechanism. Use at your own risk.
    """
    body = params["body"]
    entries = body["entries"]

    succeeded_hosts: List[watolib.CREHost] = []
    failed_hosts: Dict[HostName, str] = {}
    for update_detail in entries:
        host_name = update_detail["host_name"]
        new_attributes = update_detail["attributes"]
        update_attributes = update_detail["update_attributes"]
        remove_attributes = update_detail["remove_attributes"]
        check_hostname(host_name)
        host: watolib.CREHost = watolib.Host.load_host(host_name)
        if new_attributes:
            host.edit(new_attributes, None)

        if update_attributes:
            host.update_attributes(update_attributes)

        faulty_attributes = []
        for attribute in remove_attributes:
            if not host.has_explicit_attribute(attribute):
                faulty_attributes.append(attribute)

        if faulty_attributes:
            failed_hosts[host_name] = f"Failed to remove {', '.join(faulty_attributes)}"
            continue

        if remove_attributes:
            host.clean_attributes(remove_attributes)

        succeeded_hosts.append(host)

    return _bulk_host_action_response(failed_hosts, succeeded_hosts)


@Endpoint(
    constructors.object_action_href("host_config", "{host_name}", action_name="rename"),
    "cmk/rename",
    method="put",
    path_params=[HOST_NAME],
    etag="both",
    additional_status_codes=[409, 422],
    status_descriptions={
        409: "There are pending changes not yet activated.",
        422: "The host could not be renamed.",
    },
    request_schema=request_schemas.RenameHost,
    response_schema=response_schemas.HostConfigSchema,
    permissions_required=permissions.AllPerm(
        [
            *PERMISSIONS.perms,
            permissions.Perm("wato.edit_hosts"),
            permissions.Perm("wato.rename_hosts"),
        ]
    ),
)
def rename_host(params):
    """Rename a host"""
    user.need_permission("wato.rename_hosts")
    if activate_changes.get_pending_changes_info():
        return problem(
            status=409,
            title="Pending changes are present",
            detail="Please activate all pending changes before executing a host rename process",
        )
    host_name = params["host_name"]
    host: watolib.CREHost = watolib.Host.load_host(host_name)
    new_name = params["body"]["new_name"]
    _, auth_problems = perform_rename_hosts([(host.folder(), host_name, new_name)])
    if auth_problems:
        return problem(
            status=422,
            title="Rename process failed",
            detail=f"It was not possible to rename the host {host_name} to {new_name}",
        )
    return _serve_host(host, effective_attributes=False)


@Endpoint(
    constructors.object_action_href("host_config", "{host_name}", action_name="move"),
    "cmk/move",
    method="post",
    path_params=[HOST_NAME],
    etag="both",
    request_schema=request_schemas.MoveHost,
    response_schema=response_schemas.HostConfigSchema,
    permissions_required=permissions.AllPerm(
        [
            *PERMISSIONS.perms,
            permissions.Perm("wato.edit_hosts"),
            permissions.Perm("wato.move_hosts"),
        ]
    ),
)
def move(params):
    """Move a host to another folder"""
    user.need_permission("wato.move_hosts")
    host_name = params["host_name"]
    host: watolib.CREHost = watolib.Host.load_host(host_name)
    _require_host_etag(host)
    current_folder = host.folder()
    target_folder: CREFolder = params["body"]["target_folder"]
    if target_folder is current_folder:
        return problem(
            status=400,
            title="Invalid move action",
            detail="The host is already part of the specified target folder",
        )

    try:
        current_folder.move_hosts([host_name], target_folder)
    except MKUserError as exc:
        return problem(
            status=400,
            title="Problem moving host",
            detail=exc.message,
        )
    return _serve_host(host, effective_attributes=False)


@Endpoint(
    constructors.object_href("host_config", "{host_name}"),
    ".../delete",
    method="delete",
    path_params=[HOST_NAME],
    output_empty=True,
    permissions_required=PERMISSIONS,
)
def delete(params):
    """Delete a host"""
    host_name = params["host_name"]
    # Parameters can't be validated through marshmallow yet.
    check_hostname(host_name, should_exist=True)
    host: watolib.CREHost = watolib.Host.load_host(host_name)
    host.folder().delete_hosts([host.name()])
    return Response(status=204)


@Endpoint(
    constructors.domain_type_action_href("host_config", "bulk-delete"),
    ".../delete",
    method="post",
    request_schema=request_schemas.BulkDeleteHost,
    permissions_required=PERMISSIONS,
    output_empty=True,
)
def bulk_delete(params):
    """Bulk delete hosts"""
    body = params["body"]
    for host_name in body["entries"]:
        host = watolib.Host.load_host(host_name)
        host.folder().delete_hosts([host.name()])
    return Response(status=204)


@Endpoint(
    constructors.object_href("host_config", "{host_name}"),
    "cmk/show",
    method="get",
    path_params=[HOST_NAME],
    query_params=[
        {
            "effective_attributes": fields.Boolean(
                load_default=False,
                required=False,
                example=False,
                description=(
                    "Show all effective attributes, which affect this host, not just the "
                    "attributes which were set on this host specifically. This includes "
                    "all attributes of all of this host's parent folders."
                ),
            )
        }
    ],
    etag="output",
    response_schema=response_schemas.HostConfigSchema,
    permissions_required=permissions.Optional(permissions.Perm("wato.see_all_folders")),
)
def show_host(params):
    """Show a host"""
    host_name = params["host_name"]
    host: watolib.CREHost = watolib.Host.load_host(host_name)
    return _serve_host(host, effective_attributes=params["effective_attributes"])


def _serve_host(host, effective_attributes=False):
    response = Response()
    response.set_data(json.dumps(serialize_host(host, effective_attributes)))
    response.set_content_type("application/json")
    etag = constructors.etag_of_dict(_host_etag_values(host))
    response.headers.add("ETag", etag.to_header())
    return response


def serialize_host(host: watolib.CREHost, effective_attributes: bool):
    extensions = {
        "folder": host.folder().path(),
        "attributes": host.attributes(),
        "effective_attributes": host.effective_attributes() if effective_attributes else None,
        "is_cluster": host.is_cluster(),
        "is_offline": host.is_offline(),
        "cluster_nodes": host.cluster_nodes(),
    }

    agent_links = []
    if not cmk_version.is_raw_edition():
        import cmk.gui.cee.agent_bakery as agent_bakery  # pylint: disable=no-name-in-module

        for agent_type in sorted(agent_bakery.agent_package_types().keys()):
            agent_links.append(
                constructors.link_rel(
                    rel="cmk/download",
                    href="{}?{}".format(
                        constructors.domain_type_action_href("agent", "download"),
                        urlencode({"os_type": agent_type, "host_name": host.id()}),
                    ),
                    method="get",
                    title=f"Download the {agent_type} agent of the host.",
                )
            )

    return constructors.domain_object(
        domain_type="host_config",
        identifier=host.id(),
        title=host.alias() or host.name(),
        links=[
            constructors.link_rel(
                rel="cmk/folder_config",
                href=constructors.object_href("folder_config", folder_slug(host.folder())),
                method="get",
                title="The folder config of the host.",
            ),
        ]
        + agent_links,
        extensions=extensions,
    )


def _except_keys(dict_: Dict[str, Any], exclude_keys: List[str]) -> Dict[str, Any]:
    """Removes some keys from a dict.

    Examples:
        >>> _except_keys({'a': 'b', 'remove_me': 'hurry up'}, ['remove_me'])
        {'a': 'b'}

    """
    if not exclude_keys:
        return dict_
    return {key: value for key, value in dict_.items() if key not in exclude_keys}


def _require_host_etag(host):
    etag_values = _host_etag_values(host)
    constructors.require_etag(
        constructors.etag_of_dict(etag_values),
        error_details=etag_values,
    )


def _host_etag_values(host):
    # FIXME: Through some not yet fully explored effect, we do not get the actual persisted
    #        timestamp in the meta_data section but rather some other timestamp. This makes the
    #        reported ETag a different one than the one which is accepted by the endpoint.
    return {
        "name": host.name(),
        "attributes": _except_keys(host.attributes(), ["meta_data"]),
        "cluster_nodes": host.cluster_nodes(),
    }
