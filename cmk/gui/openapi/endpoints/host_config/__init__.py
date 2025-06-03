#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import itertools
import operator
from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import Any
from urllib.parse import urlparse

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId

from cmk.gui import fields as gui_fields
from cmk.gui.background_job import InitialStatusArgs, JobTarget
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKAuthException, MKUserError
from cmk.gui.fields.fields_filter import FieldsFilter, make_filter
from cmk.gui.fields.utils import BaseSchema
from cmk.gui.http import request, Response
from cmk.gui.logged_in import user
from cmk.gui.openapi.endpoints.common_fields import field_fields_filter, field_include_links
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
from cmk.gui.openapi.shared_endpoint_families.host_config import HOST_CONFIG_FAMILY
from cmk.gui.openapi.utils import EXT, problem, serve_json
from cmk.gui.utils import permission_verification as permissions
from cmk.gui.wato.pages.host_rename import rename_hosts_job_entry_point, RenameHostsJobArgs
from cmk.gui.watolib import bakery
from cmk.gui.watolib.activate_changes import has_pending_changes
from cmk.gui.watolib.check_mk_automations import delete_hosts
from cmk.gui.watolib.configuration_bundle_store import is_locked_by_quick_setup
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


def host_fields_filter(
    *, is_collection: bool, include_links: bool, effective_attributes: bool
) -> FieldsFilter:
    response_fields_filters: dict[str, FieldsFilter] = {}
    if not include_links:
        response_fields_filters["links"] = make_filter(this_is="excluded")
    if not effective_attributes:
        response_fields_filters["extensions"] = make_filter(
            exclude={"effective_attributes": make_filter(this_is="excluded")}
        )

    if not response_fields_filters:
        # no filters, all fields are included
        return make_filter(this_is="included")

    fields_filter = make_filter(exclude=response_fields_filters)
    if not is_collection:
        return fields_filter

    return make_filter(exclude={"value": fields_filter})


def _fields_filter_from_params(params: Mapping[str, Any], *, is_collection: bool) -> FieldsFilter:
    if "fields" in params:
        return params["fields"]

    return host_fields_filter(
        is_collection=is_collection,
        include_links=params.get(
            "include_links", True
        ),  # actual default is false, we use get in case it's not a parameter
        effective_attributes=params.get(
            "effective_attributes", True
        ),  # actual default is false, we use get in case it's not a parameter
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
    family_name=HOST_CONFIG_FAMILY.name,
)
def create_host(params: Mapping[str, Any]) -> Response:
    """Create a host"""
    user.need_permission("wato.edit")
    body = params["body"]
    host_name: HostName = body["host_name"]
    folder: Folder = body["folder"]

    # is_cluster is defined as "cluster_hosts is not None"
    folder.create_hosts(
        [(host_name, body["attributes"], None)], pprint_value=active_config.wato_pprint_config
    )
    if params[BAKE_AGENT_PARAM_NAME]:
        bakery.try_bake_agents_for_hosts([host_name], debug=active_config.debug)

    host = Host.load_host(host_name)
    return _serve_host(
        host,
        host_fields_filter(is_collection=False, include_links=True, effective_attributes=False),
    )


@Endpoint(
    constructors.collection_href("host_config", "clusters"),
    "cmk/create_cluster",
    method="post",
    etag="output",
    request_schema=CreateClusterHost,
    response_schema=HostConfigSchema,
    permissions_required=with_access_check_permission(PERMISSIONS),
    query_params=[BAKE_AGENT_PARAM],
    family_name=HOST_CONFIG_FAMILY.name,
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
        pprint_value=active_config.wato_pprint_config,
    )
    if params[BAKE_AGENT_PARAM_NAME]:
        bakery.try_bake_agents_for_hosts([host_name], debug=active_config.debug)

    host = Host.load_host(host_name)
    return _serve_host(
        host,
        host_fields_filter(is_collection=False, include_links=True, effective_attributes=False),
    )


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
    family_name=HOST_CONFIG_FAMILY.name,
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

        folder.create_validated_hosts(
            validated_entries, pprint_value=active_config.wato_pprint_config
        )
        succeeded_hosts.extend(entry[0] for entry in validated_entries)

    if params[BAKE_AGENT_PARAM_NAME]:
        bakery.try_bake_agents_for_hosts(succeeded_hosts, debug=active_config.debug)

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


class SearchFilter:
    hostnames_filter = "hostnames"
    site_filter = "site"

    @classmethod
    def from_params(cls, params: Mapping[str, Any]) -> "SearchFilter":
        return cls(
            hostnames=params.get(cls.hostnames_filter, []),
            site=params.get(cls.site_filter),
        )

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


def _iter_hosts_with_permission(folder: Folder) -> Iterable[Host]:
    yield from (host for host in folder.hosts().values() if host.permissions.may("read"))
    for subfolder in folder.subfolders():
        if not subfolder.permissions.may("read"):
            continue  # skip all hosts if folder isn't readable

        yield from _iter_hosts_with_permission(subfolder)


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
        field_fields_filter(),
        {
            SearchFilter.hostnames_filter: fields.List(
                fields.String(
                    description="A list of host names to filter the result by.",
                    required=False,
                    example="host1",
                ),
                description="Filter the result by a list of host names.",
                required=False,
                example=["host1", "host2"],
                minLength=1,
            ),
            SearchFilter.site_filter: fields.String(
                description="Filter the result by a specific site.",
                required=False,
                example="site1",
            ),
        },
    ],
    family_name=HOST_CONFIG_FAMILY.name,
)
def list_hosts(params: Mapping[str, Any]) -> Response:
    """Show all hosts"""
    root_folder = folder_tree().root_folder()
    hosts_filter = SearchFilter.from_params(params)
    if user.may("wato.see_all_folders"):
        # allowed to see all hosts, no need for individual permission checks
        hosts: Iterable[Host] = root_folder.all_hosts_recursively().values()
    else:
        hosts = _iter_hosts_with_permission(root_folder)

    return serve_host_collection(
        filter(hosts_filter, hosts),
        fields_filter=_fields_filter_from_params(params, is_collection=True),
    )


def serve_host_collection(
    hosts: Iterable[Host], *, fields_filter: FieldsFilter | None = None
) -> Response:
    return serve_json(_host_collection(hosts, fields_filter=fields_filter))


def _host_collection(
    hosts: Iterable[Host],
    *,
    fields_filter: FieldsFilter | None = None,
) -> dict[str, Any]:
    fields_filter = fields_filter or host_fields_filter(
        is_collection=True, include_links=False, effective_attributes=False
    )
    value_filter = fields_filter.get_nested_fields("value")
    return fields_filter.apply(
        {
            "id": "host",
            "domainType": "host_config",
            "value": (
                [
                    serialize_host(
                        host,
                        fields_filter=value_filter,
                    )
                    for host in hosts
                ]
                if value_filter.is_included()
                else None
            ),
            "links": [constructors.link_rel("self", constructors.collection_href("host_config"))],
        }
    )


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
    family_name=HOST_CONFIG_FAMILY.name,
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
    host.edit(host.attributes, nodes, pprint_value=active_config.wato_pprint_config)

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
    family_name=HOST_CONFIG_FAMILY.name,
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
        host.edit(
            new_attributes, host.cluster_nodes(), pprint_value=active_config.wato_pprint_config
        )

    if update_attributes := body.get("update_attributes"):
        host.update_attributes(update_attributes, pprint_value=active_config.wato_pprint_config)

    if remove_attributes := body.get("remove_attributes"):
        faulty_attributes = []
        for attribute in remove_attributes:
            if attribute not in host.attributes:
                faulty_attributes.append(attribute)

        host.clean_attributes(
            remove_attributes, pprint_value=active_config.wato_pprint_config
        )  # silently ignores missing attributes

        if faulty_attributes:
            return problem(
                status=400,
                title="Some attributes were not removed",
                detail=f"The following attributes were not removed since they didn't exist: {', '.join(faulty_attributes)}",
            )

    return _serve_host(
        host,
        host_fields_filter(is_collection=False, include_links=True, effective_attributes=False),
    )


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
    family_name=HOST_CONFIG_FAMILY.name,
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

    hosts_by_folder: dict[Folder, list[Host]] = {}
    host_name_to_updates: dict[HostName, list[dict[str, Any]]] = {}
    for update_detail in body["entries"]:
        host = Host.load_host(update_detail["host_name"])
        hosts_by_folder.setdefault(host.folder(), []).append(host)
        host_name_to_updates.setdefault(host.name(), []).append(update_detail)

    for folder, hosts in hosts_by_folder.items():
        pending_changes: list[tuple[Host, str, list[SiteId]]] = []
        for host in hosts:
            for update_detail in host_name_to_updates[host.name()]:
                if not _validate_host_attributes_for_quick_setup(host, update_detail):
                    failed_hosts[host.name()] = "Host is locked by Quick setup."
                    continue

                attributes: HostAttributes = (
                    update_detail["attributes"]
                    if "attributes" in update_detail
                    else host.attributes.copy()
                )

                if update_attributes := update_detail.get("update_attributes"):
                    attributes.update(update_attributes)

                faulty_attributes = []
                if remove_attributes := update_detail.get("remove_attributes"):
                    for attribute in remove_attributes:
                        if attribute in attributes:
                            # mypy expects literal keys for typed dicts
                            del attributes[attribute]  # type: ignore[misc]
                        else:
                            faulty_attributes.append(attribute)

                diff, affected_sites = host.apply_edit(attributes, host.cluster_nodes())
                pending_changes.append((host, diff, affected_sites))

                if faulty_attributes:
                    failed_hosts[host.name()] = f"Failed to remove {', '.join(faulty_attributes)}"
                else:
                    succeeded_hosts.append(host)

        # skip save if no changes were made, presumably due to quick setup lock
        if pending_changes:
            folder.save_hosts(pprint_value=active_config.wato_pprint_config)
            for host, diff, affected_sites in pending_changes:
                host.add_edit_host_change(diff, affected_sites)

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
    family_name=HOST_CONFIG_FAMILY.name,
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
        JobTarget(
            callable=rename_hosts_job_entry_point,
            args=RenameHostsJobArgs(
                renamings=[(host.folder().path(), host_name, new_name)],
                site_configs=active_config.sites,
                pprint_value=active_config.wato_pprint_config,
                use_git=active_config.wato_use_git,
                debug=active_config.debug,
            ),
        ),
        InitialStatusArgs(
            title=f"Renaming of {host_name} -> {new_name}",
            lock_wato=True,
            stoppable=False,
            estimated_duration=background_job.get_status().duration,
            user=str(user.id) if user.id else None,
        ),
    )
    if result.is_error():
        return problem(status=409, title="Conflict", detail=str(result.error))

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
            "The renaming job is still running. Redirecting to the 'Wait for completion' endpoint."
        ),
        404: "There is no running renaming job",
    },
    additional_status_codes=[302, 404],
    output_empty=True,
    family_name=HOST_CONFIG_FAMILY.name,
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
    family_name=HOST_CONFIG_FAMILY.name,
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
        current_folder.move_hosts(
            [host_name], target_folder, pprint_value=active_config.wato_pprint_config
        )
    except MKAuthException:
        return problem(
            status=403,
            title="Permission denied",
            detail=f"You lack the permissions to move host {host.name()} to {folder_slug(target_folder)}.",
        )
    return _serve_host(
        host,
        host_fields_filter(is_collection=False, include_links=True, effective_attributes=False),
    )


@Endpoint(
    constructors.object_href("host_config", "{host_name}"),
    ".../delete",
    method="delete",
    path_params=[HOST_NAME],
    output_empty=True,
    permissions_required=with_access_check_permission(PERMISSIONS),
    family_name=HOST_CONFIG_FAMILY.name,
)
def delete(params: Mapping[str, Any]) -> Response:
    """Delete a host"""
    user.need_permission("wato.edit")
    host: Host = Host.load_host(params["host_name"])
    host.folder().delete_hosts(
        [host.name()],
        automation=delete_hosts,
        pprint_value=active_config.wato_pprint_config,
        debug=active_config.debug,
    )
    return Response(status=204)


@Endpoint(
    constructors.domain_type_action_href("host_config", "bulk-delete"),
    ".../delete",
    method="post",
    request_schema=BulkDeleteHost,
    permissions_required=with_access_check_permission(PERMISSIONS),
    output_empty=True,
    family_name=HOST_CONFIG_FAMILY.name,
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
        folder.delete_hosts(
            list(hostnames_per_folder),
            automation=delete_hosts,
            pprint_value=active_config.wato_pprint_config,
            debug=active_config.debug,
        )

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
    family_name=HOST_CONFIG_FAMILY.name,
)
def show_host(params: Mapping[str, Any]) -> Response:
    """Show a host"""
    host_name = params["host_name"]
    host: Host = Host.load_host(host_name)
    return _serve_host(
        host,
        _fields_filter_from_params(params, is_collection=False),
    )


def _serve_host(host: Host, fields_filter: FieldsFilter) -> Response:
    response = serve_json(serialize_host(host, fields_filter=fields_filter))
    return constructors.response_with_etag_created_from_dict(response, _host_etag_values(host))


agent_links_hook: Callable[[HostName], list[LinkType]] = lambda h: []


def serialize_host(
    host: Host,
    *,
    fields_filter: FieldsFilter,
) -> DomainObject:
    extensions = (
        {
            "folder": "/" + host.folder().path(),
            "attributes": host.attributes,
            "effective_attributes": (
                host.effective_attributes()
                if "extensions.effective_attributes" in fields_filter
                else None
            ),
            "is_cluster": host.is_cluster(),
            "is_offline": host.is_offline(),
            "cluster_nodes": host.cluster_nodes(),
        }
        if "extensions" in fields_filter
        else None
    )

    if "links" in fields_filter:
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
        include_links="links" in fields_filter,
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


def register(endpoint_registry: EndpointRegistry, *, ignore_duplicates: bool) -> None:
    endpoint_registry.register(create_host, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(create_cluster_host, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(bulk_create_hosts, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(list_hosts, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(update_nodes, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(update_host, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(bulk_update_hosts, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(rename_host, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(
        renaming_job_wait_for_completion, ignore_duplicates=ignore_duplicates
    )
    endpoint_registry.register(move, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(delete, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(bulk_delete, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(show_host, ignore_duplicates=ignore_duplicates)
