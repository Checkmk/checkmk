#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="mutable-override"

from typing import Literal

from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.framework.model.base_models import DomainObjectModel, LinkableModel

ServiceDiscoveryRunState = Literal["initialized", "running", "finished", "stopped", "exception"]


@api_model
class ServiceDiscoveryRunLogsModel:
    result: list[str] = api_field(description="The result messages")
    progress: list[str] = api_field(description="The progress messages")


@api_model
class ServiceDiscoveryRunExtensionsModel:
    active: bool = api_field(description="Whether the service discovery run is active")
    state: ServiceDiscoveryRunState = api_field(
        description="Current state of the service discovery run"
    )
    logs: ServiceDiscoveryRunLogsModel = api_field(
        description="The logs of the service discovery run"
    )


@api_model
class ServiceDiscoveryRunModel(DomainObjectModel):
    domainType: Literal["service_discovery_run"] = api_field(
        description="The domain type of the object"
    )
    extensions: ServiceDiscoveryRunExtensionsModel = api_field(
        description="Additional information about the service discovery run"
    )


@api_model
class ServiceDiscoveryResultCheckTableValueExtensionsModel:
    host_name: str = api_field(description="The name of the host")
    check_plugin_name: str = api_field(description="The name of the check plugin")
    service_name: str = api_field(description="The name of the service")
    service_item: str | None = api_field(description="The name of the service item")
    service_phase: str = api_field(description="The name of the service phase")


@api_model
class ServiceDiscoveryResultCheckTableValueModel(LinkableModel):
    id: str = api_field(description="The name of the check")
    memberType: Literal["property"] = api_field(description="The type of this member.")
    value: str = api_field(description="Current service phase of the check")
    format: Literal["string"] = api_field(description="The format of the property value.")
    title: str = api_field(description="Current service phase of the check")
    extensions: ServiceDiscoveryResultCheckTableValueExtensionsModel = api_field(
        description="Additional information about the check"
    )


@api_model
class ServiceDiscoveryResultHostLabelValueModel:
    value: str = api_field(description="The value of the host label")
    plugin_name: str | None = api_field(
        description="The name of the plugin that discovered the host label",
        default=None,
    )


@api_model
class ServiceDiscoveryResultExtensionsModel:
    check_table: dict[str, ServiceDiscoveryResultCheckTableValueModel] = api_field(
        description="The changed checks for this host"
    )
    host_labels: dict[str, ServiceDiscoveryResultHostLabelValueModel] = api_field(
        description="The labels of the host"
    )
    vanished_labels: dict[str, ServiceDiscoveryResultHostLabelValueModel] = api_field(
        description="The labels that have vanished"
    )
    changed_labels: dict[str, ServiceDiscoveryResultHostLabelValueModel] = api_field(
        description="The labels that have changed"
    )


@api_model
class ServiceDiscoveryResultModel(DomainObjectModel):
    domainType: Literal["service_discovery"] = api_field(
        description="The domain type of the object"
    )
    extensions: ServiceDiscoveryResultExtensionsModel = api_field(
        description="Additional information about the service discovery result"
    )
