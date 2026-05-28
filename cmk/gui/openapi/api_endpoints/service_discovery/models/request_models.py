#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated, Literal

from cmk.ccc.hostaddress import HostName
from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.framework.model.converter import HostConverter, TypedPlainValidator
from cmk.gui.watolib.hosts_and_folders import Host

_DISCOVERY_MODE_DESCRIPTION = """The mode of the discovery action. The 'refresh' mode starts a new \
service discovery which will contact the host and identify undecided and vanished services and \
host labels. Those services and host labels can be added or removed accordingly with the 'fix_all' \
mode. The 'tabula_rasa' mode combines these two procedures. The 'new', 'remove', 'only_host_labels' \
and 'only_service_labels' modes give you more granular control. Both the 'tabula_rasa' and \
'refresh' modes will start a background job and the endpoint will return a redirect to the \
'wait-for-completion' endpoint. All other modes will return an immediate result instead. Keep in \
mind that the non background job modes only work with scanned data, so you may need to run \
"refresh" first. The corresponding user interface option for each discovery mode is shown below.

 * `new` - Monitor undecided services
 * `remove` - Remove vanished services
 * `fix_all` - Accept all
 * `tabula_rasa` - Remove all and find new
 * `refresh` - Rescan
 * `only_host_labels` - Update host labels
 * `only_service_labels` - Update service labels
"""


@api_model
class UpdateDiscoveryPhaseModel:
    check_type: str = api_field(
        description="The name of the check which this service uses.",
        example="df",
    )
    service_item: str | None = api_field(
        description="The value uniquely identifying the service on a given host.",
        example="/home",
    )
    target_phase: Literal[
        "active",
        "changed",
        "clustered_ignored",
        "clustered_monitored",
        "clustered_undecided",
        "clustered_vanished",
        "custom",
        "ignored",
        "ignored_active",
        "ignored_custom",
        "legacy",
        "legacy_ignored",
        "manual",
        "monitored",
        "removed",
        "undecided",
        "vanished",
    ] = api_field(
        description="The target phase of the service.",
        example="monitored",
    )


@api_model
class DiscoverServicesModel:
    host_name: Annotated[
        Host,
        TypedPlainValidator(str, HostConverter().host),
    ] = api_field(
        description="The host of the service which shall be updated.",
        example="example.com",
    )
    mode: Literal[
        "new",
        "remove",
        "fix_all",
        "refresh",
        "only_host_labels",
        "only_service_labels",
        "tabula_rasa",
    ] = api_field(
        description=_DISCOVERY_MODE_DESCRIPTION,
        example="refresh",
        default="fix_all",
    )


@api_model
class BulkDiscoveryOptionsModel:
    monitor_undecided_services: bool = api_field(
        description="The option whether to monitor undecided services or not.",
        example=True,
        default=False,
    )
    remove_vanished_services: bool = api_field(
        description="The option whether to remove vanished services or not.",
        example=True,
        default=False,
    )
    update_service_labels: bool = api_field(
        description="The option whether to update service labels or not.",
        example=True,
        default=False,
    )
    update_service_parameters: bool = api_field(
        description="The option whether to update discovered service parameters or not.",
        example=True,
        default=False,
    )
    update_host_labels: bool = api_field(
        description="The option whether to update host labels or not.",
        example=True,
        default=False,
    )


@api_model
class BulkDiscoveryModel:
    hostnames: list[Annotated[HostName, TypedPlainValidator(str, HostConverter().host_name)]] = (
        api_field(
            description="A list of host names",
            example=["example", "sample"],
        )
    )
    options: BulkDiscoveryOptionsModel = api_field(
        description="The discovery options for the bulk discovery",
        example={
            "monitor_undecided_services": True,
            "remove_vanished_services": True,
            "update_service_labels": True,
            "update_service_parameters": True,
            "update_host_labels": True,
        },
    )
    do_full_scan: bool = api_field(
        description="The option whether to perform a full scan or not.",
        example=True,
        default=True,
    )
    bulk_size: int = api_field(
        description="The number of hosts to be handled at once.",
        example=10,
        default=10,
    )
    ignore_errors: bool = api_field(
        description="The option whether to ignore errors in single check plug-ins.",
        example=True,
        default=True,
    )
