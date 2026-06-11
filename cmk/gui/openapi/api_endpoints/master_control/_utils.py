#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from dataclasses import dataclass

from cmk.ccc.site import SiteId
from cmk.gui.openapi.framework.model.constructors import generate_links
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.utils import permission_verification as permissions
from cmk.livestatus_client import (
    Command,
    DisableEventHandlers,
    DisableFlapDetection,
    DisableNotifications,
    DisablePerformanceData,
    EnableEventHandlers,
    EnableFlapDetection,
    EnableNotifications,
    EnablePerformanceData,
    LivestatusClient,
    StartExecutingHostChecks,
    StartExecutingServiceChecks,
    StopExecutingHostChecks,
    StopExecutingServiceChecks,
)
from cmk.livestatus_client._connection import MultiSiteConnection
from cmk.livestatus_client.queries import Query, ResultRow
from cmk.livestatus_client.tables import Status
from cmk.livestatus_client.types import Column

from .models.response_models import MasterControlExtensionsModel, MasterControlModel

# Reading the status table goes through the livestatus filtering, which checks "see all" style
# permissions. These must be declared in addition to the master control snap-in permission that
# gates this capability in the GUI. "sidesnap.master_control" is registered by the sidebar snap-in
# registry, which is not loaded during spec generation, hence OkayToIgnorePerm.
PERMISSIONS = permissions.AllPerm(
    [
        permissions.OkayToIgnorePerm("sidesnap.master_control"),
        permissions.Undocumented(
            permissions.AnyPerm(
                [
                    permissions.Perm("general.see_all"),
                    permissions.OkayToIgnorePerm("bi.see_all"),
                    permissions.OkayToIgnorePerm("mkeventd.seeall"),
                ]
            )
        ),
    ]
)


@dataclass(frozen=True)
class _MasterControlToggle:
    """The livestatus status column for a setting and the commands to switch it."""

    column: Column
    enable: Command
    disable: Command


# Adding a new toggle requires: an entry here (keyed by the API field name), a field on the
# request and response models, and a line in the serialization helper below.
MASTER_CONTROL_TOGGLES: Mapping[str, _MasterControlToggle] = {
    "notifications": _MasterControlToggle(
        column=Status.enable_notifications,
        enable=EnableNotifications(),
        disable=DisableNotifications(),
    ),
    "service_checks": _MasterControlToggle(
        column=Status.execute_service_checks,
        enable=StartExecutingServiceChecks(),
        disable=StopExecutingServiceChecks(),
    ),
    "host_checks": _MasterControlToggle(
        column=Status.execute_host_checks,
        enable=StartExecutingHostChecks(),
        disable=StopExecutingHostChecks(),
    ),
    "flap_detection": _MasterControlToggle(
        column=Status.enable_flap_detection,
        enable=EnableFlapDetection(),
        disable=DisableFlapDetection(),
    ),
    "event_handlers": _MasterControlToggle(
        column=Status.enable_event_handlers,
        enable=EnableEventHandlers(),
        disable=DisableEventHandlers(),
    ),
    "performance_data": _MasterControlToggle(
        column=Status.process_performance_data,
        enable=EnablePerformanceData(),
        disable=DisablePerformanceData(),
    ),
}


def status_columns() -> list[Column]:
    return [toggle.column for toggle in MASTER_CONTROL_TOGGLES.values()]


def serialize_master_control(site_id: SiteId, row: ResultRow) -> MasterControlModel:
    """Build the response model from a status row."""
    return MasterControlModel(
        domainType="master_control",
        id=site_id,
        title=site_id,
        links=generate_links("master_control", site_id, editable=False, deletable=False),
        extensions=MasterControlExtensionsModel(
            notifications=bool(row[Status.enable_notifications.name]),
            service_checks=bool(row[Status.execute_service_checks.name]),
            host_checks=bool(row[Status.execute_host_checks.name]),
            flap_detection=bool(row[Status.enable_flap_detection.name]),
            event_handlers=bool(row[Status.enable_event_handlers.name]),
            performance_data=bool(row[Status.process_performance_data.name]),
        ),
    )


def read_master_control_state(live: MultiSiteConnection, site_id: SiteId) -> ResultRow:
    """Read the master control state of a single site.

    Raises a 404 if the site does not return exactly one status row, which happens when the site
    is unreachable.
    """
    try:
        return Query(status_columns()).fetchone(live, include_site_ids=True, only_site=site_id)
    except ValueError:
        raise ProblemException(
            status=404,
            title="Master control state unavailable",
            detail=f"Could not read the master control state of site {site_id!r}. "
            "The site may be unreachable.",
        )


def apply_master_control_changes(
    live: MultiSiteConnection, site_id: SiteId, changes: Mapping[str, bool]
) -> None:
    """Send the toggle commands for the requested changes to the site's monitoring core."""
    client = LivestatusClient(live)
    for api_field, enabled in changes.items():
        toggle = MASTER_CONTROL_TOGGLES[api_field]
        client.command(toggle.enable if enabled else toggle.disable, site_id)
