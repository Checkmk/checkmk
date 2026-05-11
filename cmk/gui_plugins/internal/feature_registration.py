#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from dataclasses import dataclass

from cmk.ccc.version import Edition
from cmk.gui.autocompleters import AutocompleterRegistry
from cmk.gui.graphing._metric_backend_registry import MetricBackendRegistry
from cmk.gui.openapi.framework.registry import VersionedEndpointRegistry
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamilyRegistry
from cmk.gui.sidebar import SnapinRegistry
from cmk.gui.watolib.config_domain_name import ConfigDomainRegistry, ConfigVariableRegistry
from cmk.gui.watolib.config_sync import ReplicationPathRegistry
from cmk.licensing.basics.options import LicenseOptions


@dataclass(frozen=True)
class RegistrationContext:
    edition: Edition
    features: LicenseOptions
    autocompleter_registry: AutocompleterRegistry
    config_domain_registry: ConfigDomainRegistry
    config_variable_registry: ConfigVariableRegistry
    endpoint_family_registry: EndpointFamilyRegistry
    metric_backend_registry: MetricBackendRegistry
    replication_path_registry: ReplicationPathRegistry
    snapin_registry: SnapinRegistry
    versioned_endpoint_registry: VersionedEndpointRegistry
    # Add more registries here as new GuiFeaturePlugin instances require them.


@dataclass(frozen=True)
class GuiFeaturePlugin:
    name: str
    register: Callable[[RegistrationContext], None]
    enabled: Callable[[RegistrationContext], bool] = lambda ctx: True
