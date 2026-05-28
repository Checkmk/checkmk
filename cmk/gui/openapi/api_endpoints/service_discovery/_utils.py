#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
from typing import Literal

from livestatus import SiteConfigurations

from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId
from cmk.gui.background_job.job import BackgroundStatusSnapshot
from cmk.gui.openapi.framework import APIVersion
from cmk.gui.openapi.framework.endpoint_link import link_to_endpoint
from cmk.gui.openapi.framework.model.base_models import LinkModel
from cmk.gui.openapi.framework.model.constructors import generate_links
from cmk.gui.openapi.restful_objects.constructors import expand_rel
from cmk.gui.site_config import site_is_local
from cmk.gui.user_sites import activation_sites
from cmk.gui.utils import permission_verification as permissions
from cmk.gui.watolib.audit_log import make_audit_log_change_hook
from cmk.gui.watolib.automations import (
    fetch_service_discovery_background_job_status,
    remote_automation_config_from_site_config,
)
from cmk.gui.watolib.hosts_and_folders import Host
from cmk.gui.watolib.pending_changes import (
    index_update_change_hook,
    PendingChanges,
    PendingChangesStore,
)
from cmk.gui.watolib.services import (
    DiscoveryAction,
    DiscoveryResult,
    DiscoveryState,
    ServiceDiscoveryBackgroundJob,
)
from cmk.utils.labels import HostLabelValueDict

from ._family import SERVICE_DISCOVERY_FAMILY
from .models.response_models import (
    ServiceDiscoveryResultCheckTableValueExtensionsModel,
    ServiceDiscoveryResultCheckTableValueModel,
    ServiceDiscoveryResultExtensionsModel,
    ServiceDiscoveryResultHostLabelValueModel,
    ServiceDiscoveryResultModel,
)

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

RO_PERMISSIONS = permissions.AllPerm(
    [
        permissions.Perm("wato.edit"),
        permissions.Perm("wato.services"),
        permissions.Perm("wato.see_all_folders"),
        # The permissions below are required to manage BackgroundJobs
        permissions.Optional(permissions.Perm("background_jobs.stop_jobs")),
        permissions.Optional(permissions.Perm("background_jobs.stop_foreign_jobs")),
        permissions.Optional(permissions.Perm("background_jobs.delete_jobs")),
        permissions.Optional(permissions.Perm("background_jobs.delete_foreign_jobs")),
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


DISCOVERY_ACTION = {
    "new": DiscoveryAction.BULK_UPDATE,
    "remove": DiscoveryAction.BULK_UPDATE,
    "fix_all": DiscoveryAction.FIX_ALL,
    "refresh": DiscoveryAction.REFRESH,
    "only_host_labels": DiscoveryAction.UPDATE_HOST_LABELS,
    "only_service_labels": DiscoveryAction.UPDATE_SERVICE_LABELS,
    "tabula_rasa": DiscoveryAction.TABULA_RASA,
}


def make_pending_changes(
    *,
    site_configs: SiteConfigurations,
    use_git: bool,
    local_site: SiteId,
    acting_user: UserId | None,
) -> PendingChanges:
    return PendingChanges(
        activation_sites=activation_sites(site_configs),
        local_site=local_site,
        acting_user=acting_user,
        store=PendingChangesStore(),
        hooks=(
            make_audit_log_change_hook(use_git=use_git),
            index_update_change_hook,
        ),
    )


def job_snapshot(
    host: Host, site_configs: SiteConfigurations, *, debug: bool
) -> BackgroundStatusSnapshot:
    if site_is_local(site_configs[(site_id := host.site_id())]):
        job = ServiceDiscoveryBackgroundJob(host.name())
        return job.get_status_snapshot()

    return fetch_service_discovery_background_job_status(
        remote_automation_config_from_site_config(site_configs[site_id]),
        host.name(),
        debug=debug,
    )


def _lookup_phase_name(internal_phase_name: str) -> str:
    for key, value in SERVICE_DISCOVERY_PHASES.items():
        if value == internal_phase_name:
            return key
    raise ValueError(f"Key {internal_phase_name} not found in dict.")


def _serialize_labels(
    labels: dict[str, HostLabelValueDict],
) -> dict[str, ServiceDiscoveryResultHostLabelValueModel]:
    return {
        name: ServiceDiscoveryResultHostLabelValueModel(
            value=label["value"],
            plugin_name=label["plugin_name"],
        )
        for name, label in labels.items()
    }


_MovePhase = Literal["monitored", "undecided", "ignored"]
_MoveRel = Literal[
    "cmk/service.move-monitored",
    "cmk/service.move-undecided",
    "cmk/service.move-ignored",
]
_MOVE_PHASES: tuple[_MovePhase, ...] = ("monitored", "undecided", "ignored")


def _move_phase_rel(target_phase: _MovePhase) -> _MoveRel:
    match target_phase:
        case "monitored":
            return "cmk/service.move-monitored"
        case "undecided":
            return "cmk/service.move-undecided"
        case "ignored":
            return "cmk/service.move-ignored"


def _move_service_link(
    *,
    version: APIVersion,
    host_url: str,
    host_name: str,
    target_phase: _MovePhase,
    check_plugin_name: str,
    service_item: str | None,
) -> LinkModel:
    # link_to_endpoint resolves the endpoint by link_relation; the resulting
    # LinkModel's rel reflects the endpoint metadata (.../modify). We override
    # rel so each link advertises its specific target phase, which API consumers
    # rely on to distinguish the three move actions.
    link = link_to_endpoint(
        family=SERVICE_DISCOVERY_FAMILY.name,
        link_relation=".../modify",
        version=version,
        host_url=host_url,
        parameters={"host_name": host_name},
        body={
            "target_phase": target_phase,
            "check_type": check_plugin_name,
            "service_item": service_item,
        },
        title=f"Move the service to {target_phase}",
    )
    link.rel = expand_rel(_move_phase_rel(target_phase))
    return link


def serialize_discovery_result(
    host: Host,
    discovery_result: DiscoveryResult,
    *,
    version: APIVersion,
    host_url: str,
) -> ServiceDiscoveryResultModel:
    host_name = host.name()
    check_table: dict[str, ServiceDiscoveryResultCheckTableValueModel] = {}
    for entry in discovery_result.check_table:
        service_phase = _lookup_phase_name(entry.check_source)
        check_table[f"{entry.check_plugin_name}-{entry.item}"] = (
            ServiceDiscoveryResultCheckTableValueModel(
                links=[
                    _move_service_link(
                        version=version,
                        host_url=host_url,
                        host_name=host_name,
                        target_phase=target_phase,
                        check_plugin_name=entry.check_plugin_name,
                        service_item=entry.item,
                    )
                    for target_phase in _MOVE_PHASES
                ],
                id=entry.description,
                memberType="property",
                value=service_phase,
                format="string",
                title=f"The service is currently {service_phase!r}",
                extensions=ServiceDiscoveryResultCheckTableValueExtensionsModel(
                    host_name=host_name,
                    check_plugin_name=entry.check_plugin_name,
                    service_name=entry.description,
                    service_item=entry.item,
                    service_phase=service_phase,
                ),
            )
        )

    return ServiceDiscoveryResultModel(
        domainType="service_discovery",
        id=f"service_discovery-{host_name}",
        title=f"Service discovery result of host {host_name}",
        links=generate_links(
            domain_type="service_discovery",
            identifier=f"service_discovery-{host_name}",
            deletable=False,
            editable=False,
        ),
        extensions=ServiceDiscoveryResultExtensionsModel(
            check_table=check_table,
            host_labels=_serialize_labels(dict(discovery_result.host_labels)),
            vanished_labels=_serialize_labels(dict(discovery_result.vanished_labels)),
            changed_labels=_serialize_labels(dict(discovery_result.changed_labels)),
        ),
    )
