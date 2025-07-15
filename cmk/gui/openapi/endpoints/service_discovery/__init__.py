#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Service discovery

A service discovery is the automatic and reliable detection of all services to be monitored on
a host.

You can find an introduction to services including service discovery in the
[Checkmk guide](https://docs.checkmk.com/latest/en/wato_services.html).
"""

import enum
from collections.abc import Mapping
from typing import Any, assert_never
from urllib.parse import urlparse

from cmk.utils.everythingtype import EVERYTHING

from cmk.checkengine.discovery import DiscoverySettings

from cmk.gui import fields as gui_fields
from cmk.gui.background_job import BackgroundStatusSnapshot
from cmk.gui.config import active_config
from cmk.gui.fields.utils import BaseSchema
from cmk.gui.http import request, Response
from cmk.gui.logged_in import user
from cmk.gui.openapi.endpoints.background_job import JobID
from cmk.gui.openapi.endpoints.host_config.request_schemas import EXISTING_HOST_NAME
from cmk.gui.openapi.restful_objects import constructors, Endpoint, response_schemas
from cmk.gui.openapi.restful_objects.constructors import domain_object, link_rel, object_property
from cmk.gui.openapi.restful_objects.parameters import HOST_NAME
from cmk.gui.openapi.restful_objects.registry import EndpointRegistry
from cmk.gui.openapi.restful_objects.type_defs import DomainObject, LinkType
from cmk.gui.openapi.utils import EXT, problem, ProblemException, serve_json
from cmk.gui.site_config import site_is_local
from cmk.gui.utils import permission_verification as permissions
from cmk.gui.watolib.automations import (
    fetch_service_discovery_background_job_status,
    LocalAutomationConfig,
    make_automation_config,
    MKAutomationException,
    RemoteAutomationConfig,
)
from cmk.gui.watolib.bulk_discovery import (
    BulkDiscoveryBackgroundJob,
    prepare_hosts_for_discovery,
    start_bulk_discovery,
)
from cmk.gui.watolib.hosts_and_folders import Host
from cmk.gui.watolib.services import (
    Discovery,
    DiscoveryAction,
    DiscoveryResult,
    DiscoveryState,
    get_check_table,
    has_discovery_action_specific_permissions,
    perform_fix_all,
    perform_host_label_discovery,
    perform_service_discovery,
    ServiceDiscoveryBackgroundJob,
)

from cmk import fields

from ._response_schemas import ServiceDiscoveryResultSchema, ServiceDiscoveryRunSchema

DISCOVERY_PERMISSIONS = permissions.AllPerm(
    [
        permissions.Perm("wato.edit"),
        permissions.Optional(permissions.Perm("wato.service_discovery_to_undecided")),
        permissions.Optional(permissions.Perm("wato.service_discovery_to_monitored")),
        permissions.Optional(permissions.Perm("wato.service_discovery_to_ignored")),
        permissions.Optional(permissions.Perm("wato.service_discovery_to_removed")),
        permissions.Optional(permissions.Perm("wato.services")),
        permissions.Undocumented(permissions.Perm("background_jobs.stop_jobs")),
        permissions.Undocumented(permissions.Perm("background_jobs.stop_foreign_jobs")),
        permissions.Undocumented(permissions.Perm("background_jobs.delete_jobs")),
        permissions.Undocumented(permissions.Perm("background_jobs.delete_foreign_jobs")),
        permissions.Undocumented(permissions.Perm("wato.see_all_folders")),
    ]
)

SERVICE_DISCOVERY_PHASES = {
    "undecided": DiscoveryState.UNDECIDED,
    "vanished": DiscoveryState.VANISHED,
    "monitored": DiscoveryState.MONITORED,
    "changed": DiscoveryState.CHANGED,
    "ignored": DiscoveryState.IGNORED,
    "removed": DiscoveryState.REMOVED,
    "manual": DiscoveryState.MANUAL,
    "active": DiscoveryState.ACTIVE,
    "ignored_active": DiscoveryState.ACTIVE_IGNORED,
    "custom": DiscoveryState.CUSTOM,
    "ignored_custom": DiscoveryState.CUSTOM_IGNORED,
    "clustered_monitored": DiscoveryState.CLUSTERED_OLD,
    "clustered_undecided": DiscoveryState.CLUSTERED_NEW,
    "clustered_vanished": DiscoveryState.CLUSTERED_VANISHED,
    "clustered_ignored": DiscoveryState.CLUSTERED_IGNORED,
    "legacy": "legacy",
    "legacy_ignored": "legacy_ignored",
}


class APIDiscoveryAction(enum.Enum):
    new = "new"
    remove = "remove"
    fix_all = "fix_all"
    refresh = "refresh"
    only_host_labels = "only_host_labels"
    only_service_labels = "only_service_labels"
    tabula_rasa = "tabula_rasa"


def _discovery_mode(default_mode: str) -> fields.String:
    # TODO: documentation should be separated for bulk discovery
    return fields.String(
        description="""The mode of the discovery action. The 'refresh' mode starts a new service
        discovery which will contact the host and identify undecided and vanished services and host
        labels. Those services and host labels can be added or removed accordingly with the
        'fix_all' mode. The 'tabula_rasa' mode combines these two procedures. The 'new', 'remove',
        'only_host_labels' and 'only_service_labels' modes give you more granular control. Both the
        'tabula_rasa' and 'refresh' modes will start a background job and the endpoint will return
        a redirect to the 'wait-for-completion' endpoint. All other modes will return an immediate
        result instead. Keep in mind that the non background job modes only work with scanned data,
        so you may need to run "refresh" first. The corresponding user interface option for each
        discovery mode is shown below.

 * `new` - Monitor undecided services
 * `remove` - Remove vanished services
 * `fix_all` - Accept all
 * `tabula_rasa` - Remove all and find new
 * `refresh` - Rescan
 * `only_host_labels` - Update host labels
 * `only_service_labels` - Update service labels
    """,
        enum=[a.value for a in APIDiscoveryAction],
        example="refresh",
        load_default=default_mode,
    )


DISCOVERY_ACTION = {
    "new": DiscoveryAction.BULK_UPDATE,
    "remove": DiscoveryAction.BULK_UPDATE,
    "fix_all": DiscoveryAction.FIX_ALL,
    "refresh": DiscoveryAction.REFRESH,
    "only_host_labels": DiscoveryAction.UPDATE_HOST_LABELS,
    "only_service_labels": DiscoveryAction.UPDATE_SERVICE_LABELS,
    "tabula_rasa": DiscoveryAction.TABULA_RASA,
}


@Endpoint(
    constructors.object_href("service_discovery", "{host_name}"),
    "cmk/list",
    method="get",
    response_schema=ServiceDiscoveryResultSchema,
    tag_group="Setup",
    path_params=[
        {
            "host_name": gui_fields.HostField(
                description="The host of the service discovery result",
                example="example.com",
                required=True,
            )
        }
    ],
    additional_status_codes=[400],
)
def show_service_discovery_result(params: Mapping[str, Any]) -> Response:
    """Show the current service discovery result"""
    host = Host.load_host(params["host_name"])

    try:
        discovery_result = get_check_table(
            host,
            DiscoveryAction.NONE,
            automation_config=make_automation_config(active_config.sites[host.site_id()]),
            raise_errors=False,
            debug=active_config.debug,
        )
    except MKAutomationException:
        pass
    else:
        return serve_json(serialize_discovery_result(host, discovery_result))

    try:
        snapshot = _job_snapshot(host)
    except MKAutomationException:
        return problem(
            status=400,
            title="Error running automation",
            detail="Could not retrieve the service discovery result",
        )
    logs = snapshot.status.loginfo
    return problem(
        status=400,
        title="Error running automation",
        detail="Could not retrieve the service discovery result",
        ext=EXT(
            {
                "job_id": snapshot.job_id,
                "state": snapshot.status.state,
                "logs": {
                    "result": logs["JobResult"],
                    "progress": logs["JobProgressUpdate"],
                    "exception": logs["JobException"],
                },
            }
        ),
    )


class UpdateDiscoveryPhase(BaseSchema):
    check_type = fields.String(
        description="The name of the check which this service uses.",
        example="df",
        required=True,
    )
    service_item = fields.String(
        description="The value uniquely identifying the service on a given host.",
        example="/home",
        required=True,
        allow_none=True,
    )
    target_phase = fields.String(
        description="The target phase of the service.",
        enum=sorted(SERVICE_DISCOVERY_PHASES.keys()),
        example="monitored",
        required=True,
    )


@Endpoint(
    constructors.object_action_href("host", "{host_name}", "update_discovery_phase"),
    ".../modify",
    method="put",
    output_empty=True,
    tag_group="Setup",
    path_params=[
        {
            "host_name": gui_fields.HostField(
                description="The host of the service which shall be updated.",
                example="example.com",
            ),
        }
    ],
    status_descriptions={
        404: "Host could not be found",
    },
    request_schema=UpdateDiscoveryPhase,
    # TODO: CMK-10911 (permissions)
    permissions_required=permissions.AnyPerm(
        [
            permissions.Optional(
                permissions.AnyPerm(
                    [
                        permissions.Perm("wato.service_discovery_to_monitored"),
                        permissions.Perm("wato.service_discovery_to_ignored"),
                        permissions.Perm("wato.service_discovery_to_undecided"),
                        permissions.Perm("wato.service_discovery_to_removed"),
                        permissions.Undocumented(permissions.Perm("wato.see_all_folders")),
                    ]
                )
            ),
        ]
    ),
)
def update_service_phase(params: Mapping[str, Any]) -> Response:
    """Update the phase of a service"""
    body = params["body"]
    host = Host.load_host(params["host_name"])
    target_phase = body["target_phase"]
    check_type = body["check_type"]
    service_item = body["service_item"]
    _update_single_service_phase(
        SERVICE_DISCOVERY_PHASES[target_phase],
        host,
        check_type,
        service_item,
        automation_config=make_automation_config(active_config.sites[host.site_id()]),
        pprint_value=active_config.wato_pprint_config,
        debug=active_config.debug,
    )
    return Response(status=204)


def _update_single_service_phase(
    target_phase: str,
    host: Host,
    check_type: str,
    service_item: str | None,
    *,
    automation_config: LocalAutomationConfig | RemoteAutomationConfig,
    pprint_value: bool,
    debug: bool,
) -> None:
    action = DiscoveryAction.SINGLE_UPDATE
    Discovery(
        host=host,
        action=action,
        update_target=target_phase,
        selected_services=((check_type, service_item),),
        user_need_permission=user.need_permission,
    ).do_discovery(
        get_check_table(
            host,
            action,
            automation_config=make_automation_config(active_config.sites[host.site_id()]),
            raise_errors=False,
            debug=debug,
        ),
        host.name(),
        automation_config=automation_config,
        pprint_value=pprint_value,
        debug=debug,
    )


@Endpoint(
    constructors.object_href("service_discovery_run", "{host_name}"),
    "cmk/show",
    method="get",
    tag_group="Setup",
    path_params=[HOST_NAME],
    response_schema=ServiceDiscoveryRunSchema,
)
def show_service_discovery_run(params: Mapping[str, Any]) -> Response:
    """Show the last service discovery background job on a host"""
    host = Host.load_host(params["host_name"])
    snapshot = _job_snapshot(host)
    job_id = snapshot.job_id
    job_status = snapshot.status
    return serve_json(
        constructors.domain_object(
            domain_type="service_discovery_run",
            identifier=job_id,
            title=f"Service discovery background job {job_id} is {job_status.state}",
            extensions={
                "active": job_status.is_active,
                "state": job_status.state,
                "logs": {
                    "result": job_status.loginfo["JobResult"],
                    "progress": job_status.loginfo["JobProgressUpdate"],
                },
            },
            deletable=False,
            editable=False,
        )
    )


@Endpoint(
    constructors.object_action_href("service_discovery_run", "{host_name}", "wait-for-completion"),
    "cmk/wait-for-completion",
    method="get",
    status_descriptions={
        204: "The service discovery has been completed.",
        302: "The service discovery is still running. Redirecting to the "
        "'Wait for completion' endpoint.",
        404: "There is no running service discovery",
    },
    path_params=[HOST_NAME],
    additional_status_codes=[302],
    output_empty=True,
)
def service_discovery_run_wait_for_completion(params: Mapping[str, Any]) -> Response:
    """Wait for service discovery completion

    This endpoint will periodically redirect on itself to prevent timeouts.
    """
    host = Host.load_host(params["host_name"])
    snapshot = _job_snapshot(host)
    if not snapshot.exists:
        raise ProblemException(
            status=404,
            title="The requested service discovery job was not found",
            detail=f"Could not find a service discovery for host {host.name()}",
        )
    if snapshot.is_active:
        response = Response(status=302)
        response.location = urlparse(request.url).path
        return response
    return Response(status=204)


class DiscoverServices(BaseSchema):
    host_name = gui_fields.HostField(
        description="The host of the service which shall be updated.",
        example="example.com",
    )
    mode = _discovery_mode(default_mode="fix_all")


_DISCOVERY_RUNNING_MSG = "A service discovery background job is currently running"


@Endpoint(
    constructors.domain_type_action_href("service_discovery_run", "start"),
    ".../update",
    method="post",
    tag_group="Setup",
    status_descriptions={
        303: "The service discovery background job has been initialized. Redirecting to the "
        "'Wait for service discovery completion' endpoint.",
        409: _DISCOVERY_RUNNING_MSG,
    },
    additional_status_codes=[303, 409],
    request_schema=DiscoverServices,
    response_schema=response_schemas.DomainObject,
    permissions_required=DISCOVERY_PERMISSIONS,
)
def execute_service_discovery(params: Mapping[str, Any]) -> Response:
    """Execute a service discovery on a host"""
    user.need_permission("wato.edit")
    body = params["body"]
    host = Host.load_host(body["host_name"])
    discovery_action = APIDiscoveryAction(body["mode"])
    return _execute_service_discovery(
        discovery_action,
        host,
        automation_config=make_automation_config(active_config.sites[host.site_id()]),
        pprint_value=active_config.wato_pprint_config,
        debug=active_config.debug,
    )


def _execute_service_discovery(
    api_discovery_action: APIDiscoveryAction,
    host: Host,
    *,
    automation_config: LocalAutomationConfig | RemoteAutomationConfig,
    pprint_value: bool,
    debug: bool,
) -> Response:
    job_snapshot = _job_snapshot(host)
    if job_snapshot.is_active:
        return problem(
            status=409,
            title="Conflict",
            detail=_DISCOVERY_RUNNING_MSG,
        )

    discovery_action = DISCOVERY_ACTION[api_discovery_action.value]
    if not has_discovery_action_specific_permissions(discovery_action, None):
        return problem(
            status=403,
            title="Permission denied",
            detail="You do not have the necessary permissions to execute this action",
        )
    discovery_result = get_check_table(
        host,
        discovery_action,
        automation_config=automation_config,
        raise_errors=False,
        debug=debug,
    )
    match api_discovery_action:
        case APIDiscoveryAction.new:
            discovery_result = perform_service_discovery(
                action=discovery_action,
                discovery_result=discovery_result,
                update_source="new",
                update_target="unchanged",
                host=host,
                selected_services=EVERYTHING,
                raise_errors=False,
                automation_config=automation_config,
                pprint_value=pprint_value,
                debug=debug,
            )
        case APIDiscoveryAction.remove:
            discovery_result = perform_service_discovery(
                action=discovery_action,
                discovery_result=discovery_result,
                update_source="vanished",
                update_target="removed",
                host=host,
                selected_services=EVERYTHING,
                raise_errors=False,
                automation_config=automation_config,
                pprint_value=pprint_value,
                debug=debug,
            )
        case APIDiscoveryAction.fix_all:
            discovery_result = perform_fix_all(
                discovery_result=discovery_result,
                host=host,
                raise_errors=False,
                automation_config=automation_config,
                pprint_value=pprint_value,
                debug=debug,
            )
        case APIDiscoveryAction.refresh | APIDiscoveryAction.tabula_rasa:
            discovery_run = _discovery_wait_for_completion_link(host.name())
            response = Response(status=303)
            response.location = urlparse(discovery_run["href"]).path
            return response
        case APIDiscoveryAction.only_host_labels:
            discovery_result = perform_host_label_discovery(
                action=discovery_action,
                discovery_result=discovery_result,
                host=host,
                raise_errors=False,
                automation_config=automation_config,
                pprint_value=pprint_value,
                debug=debug,
            )
        case APIDiscoveryAction.only_service_labels:
            discovery_result = perform_service_discovery(
                action=discovery_action,
                discovery_result=discovery_result,
                update_source="changed",
                update_target="unchanged",
                host=host,
                selected_services=EVERYTHING,
                raise_errors=False,
                automation_config=automation_config,
                pprint_value=pprint_value,
                debug=debug,
            )

        case _:
            assert_never(api_discovery_action)

    return serve_json(serialize_discovery_result(host, discovery_result))


def _discovery_wait_for_completion_link(host_name: str) -> LinkType:
    return constructors.link_endpoint(
        "cmk.gui.openapi.endpoints.service_discovery",
        "cmk/wait-for-completion",
        parameters={"host_name": host_name},
    )


def _lookup_phase_name(internal_phase_name: str) -> str:
    for key, value in SERVICE_DISCOVERY_PHASES.items():
        if value == internal_phase_name:
            return key
    raise ValueError(f"Key {internal_phase_name} not found in dict.")


def serialize_discovery_result(
    host: Host,
    discovery_result: DiscoveryResult,
) -> DomainObject:
    services = {}
    host_name = host.name()
    for entry in discovery_result.check_table:
        service_phase = _lookup_phase_name(entry.check_source)
        services[f"{entry.check_plugin_name}-{entry.item}"] = object_property(
            name=entry.description,
            title=f"The service is currently {service_phase!r}",
            value=service_phase,
            prop_format="string",
            linkable=False,
            extensions={
                "host_name": host_name,
                "check_plugin_name": entry.check_plugin_name,
                "service_name": entry.description,
                "service_item": entry.item,
                "service_phase": service_phase,
            },
            base="",
            links=[
                link_rel(
                    rel="cmk/service.move-monitored",
                    href=update_service_phase.path.format(host_name=host_name),
                    body_params={
                        "target_phase": "monitored",
                        "check_type": entry.check_plugin_name,
                        "service_item": entry.item,
                    },
                    method="put",
                    title="Move the service to monitored",
                ),
                link_rel(
                    rel="cmk/service.move-undecided",
                    href=update_service_phase.path.format(host_name=host_name),
                    body_params={
                        "target_phase": "undecided",
                        "check_type": entry.check_plugin_name,
                        "service_item": entry.item,
                    },
                    method="put",
                    title="Move the service to undecided",
                ),
                link_rel(
                    rel="cmk/service.move-ignored",
                    href=update_service_phase.path.format(host_name=host_name),
                    body_params={
                        "target_phase": "ignored",
                        "check_type": entry.check_plugin_name,
                        "service_item": entry.item,
                    },
                    method="put",
                    title="Move the service to ignored",
                ),
            ],
        )

    return domain_object(
        domain_type="service_discovery",
        identifier=f"service_discovery-{host_name}",
        title=f"Service discovery result of host {host_name}",
        editable=False,
        deletable=False,
        extensions={
            "check_table": services,
            "host_labels": discovery_result.host_labels,
            "vanished_labels": discovery_result.vanished_labels,
            "changed_labels": discovery_result.changed_labels,
        },
    )


# Bulk discovery

JOB_ID = {
    "job_id": fields.String(
        description="The unique identifier of the background job executing the bulk discovery",
        example="bulk_discovery",
        required=True,
    ),
}


class BulkDiscoveryOptions(BaseSchema):
    monitor_undecided_services = fields.Boolean(
        required=False,
        description="The option whether to monitor undecided services or not.",
        example=True,
        load_default=False,
    )
    remove_vanished_services = fields.Boolean(
        required=False,
        description="The option whether to remove vanished services or not.",
        example=True,
        load_default=False,
    )
    update_service_labels = fields.Boolean(
        required=False,
        description="The option whether to update service labels or not.",
        example=True,
        load_default=False,
    )
    update_service_parameters = fields.Boolean(
        required=False,
        description="The option whether to update discovered service parameters or not.",
        example=True,
        load_default=False,
    )
    update_host_labels = fields.Boolean(
        required=False,
        description="The option whether to update host labels or not.",
        example=True,
        load_default=False,
    )


class BulkDiscovery(BaseSchema):
    hostnames = fields.List(
        EXISTING_HOST_NAME,
        required=True,
        example=["example", "sample"],
        description="A list of host names",
    )
    options = fields.Nested(
        BulkDiscoveryOptions,
        description="The discovery options for the bulk discovery",
        required=True,
        example={
            "monitor_undecided_services": True,
            "remove_vanished_services": True,
            "update_service_labels": True,
            "update_service_parameters": True,
            "update_host_labels": True,
        },
    )
    do_full_scan = fields.Boolean(
        required=False,
        description="The option whether to perform a full scan or not.",
        example=True,
        load_default=True,
    )
    bulk_size = fields.Integer(
        required=False,
        description="The number of hosts to be handled at once.",
        example=10,
        load_default=10,
    )
    ignore_errors = fields.Boolean(
        required=False,
        description="The option whether to ignore errors in single check plug-ins.",
        example=True,
        load_default=True,
    )


@Endpoint(
    constructors.domain_type_action_href("discovery_run", "bulk-discovery-start"),
    "cmk/activate",
    method="post",
    additional_status_codes=[303],
    request_schema=BulkDiscovery,
    output_empty=True,
    status_descriptions={
        303: "The bulk discovery job has been started in the background."
        "Redirecting to the 'Get background job status snapshot' endpoint."
    },
)
def execute_bulk_discovery(params: Mapping[str, Any]) -> Response:
    """Start a bulk discovery job

    This endpoint will start a bulk discovery background job. Only one bulk discovery job can run
    at a time. An active bulk discovery job will block other bulk discovery jobs from running until
    the active job is finished.
    """
    # TODO: documentation should be adjusted; initial fix for resolving tests
    body = params["body"]
    job = BulkDiscoveryBackgroundJob()

    options = body["options"]
    discovery_settings = DiscoverySettings(
        update_host_labels=options["update_host_labels"],
        add_new_services=options["monitor_undecided_services"],
        remove_vanished_services=options["remove_vanished_services"],
        update_changed_service_labels=options["update_service_labels"],
        update_changed_service_parameters=options["update_service_parameters"],
    )
    hosts_to_discover = prepare_hosts_for_discovery(body["hostnames"])
    if (
        result := start_bulk_discovery(
            job,
            hosts_to_discover,
            discovery_settings,
            body["do_full_scan"],
            body["ignore_errors"],
            body["bulk_size"],
            pprint_value=active_config.wato_pprint_config,
            debug=active_config.debug,
        )
    ).is_error():
        raise result.error

    background_job_status_link = constructors.link_endpoint(
        module_name="cmk.gui.openapi.endpoints.background_job",
        rel="cmk/show",
        parameters={JobID.field_name: job.get_job_id()},
    )
    response = Response(status=303)
    response.location = urlparse(background_job_status_link["href"]).path
    return response


def _job_snapshot(host: Host) -> BackgroundStatusSnapshot:
    if site_is_local(active_config.sites[(site_id := host.site_id())]):
        job = ServiceDiscoveryBackgroundJob(host.name())
        return job.get_status_snapshot()

    return fetch_service_discovery_background_job_status(
        RemoteAutomationConfig.from_site_config(active_config.sites[site_id]),
        host.name(),
        debug=active_config.debug,
    )


def register(endpoint_registry: EndpointRegistry, *, ignore_duplicates: bool) -> None:
    endpoint_registry.register(show_service_discovery_result, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(update_service_phase, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(show_service_discovery_run, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(
        service_discovery_run_wait_for_completion, ignore_duplicates=ignore_duplicates
    )
    endpoint_registry.register(execute_service_discovery, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(execute_bulk_discovery, ignore_duplicates=ignore_duplicates)
