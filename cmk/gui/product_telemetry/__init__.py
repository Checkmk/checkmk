#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.pages import PageRegistry
from cmk.gui.permissions import PermissionRegistry
from cmk.gui.product_telemetry import _permissions, global_config
from cmk.gui.product_telemetry import download as telemetry_download_page
from cmk.gui.watolib.config_domain_name import (
    ConfigDomainRegistry,
    ConfigVariableGroupRegistry,
    ConfigVariableRegistry,
)
from cmk.gui.watolib.config_sync import (
    ReplicationPath,
    ReplicationPathRegistry,
    ReplicationPathType,
)


def register(
    page_registry: PageRegistry,
    permission_registry: PermissionRegistry,
    config_domain_registry: ConfigDomainRegistry,
    config_variable_registry: ConfigVariableRegistry,
    config_variable_group_registry: ConfigVariableGroupRegistry,
    replication_path_registry: ReplicationPathRegistry,
) -> None:
    telemetry_download_page.register(page_registry)
    _permissions.register(permission_registry)
    config_domain_registry.register(global_config.ConfigDomainProductTelemetry())
    config_variable_group_registry.register(global_config.ConfigVariableGroupProductTelemetry)
    config_variable_registry.register(global_config.ConfigVariableProductTelemetry)

    replication_path_registry.register(
        ReplicationPath.make(
            ty=ReplicationPathType.FILE,
            ident=global_config.PRODUCT_TELEMETRY_CONFIG_ID,
            site_path=str(global_config.PRODUCT_TELEMETRY_CONFIG_FILE_RELATIVE),
        )
    )
