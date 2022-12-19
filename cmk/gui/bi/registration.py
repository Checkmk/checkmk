#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.permissions import PermissionRegistry, PermissionSectionRegistry
from cmk.gui.views.data_source import DataSourceRegistry

from .permissions import PermissionBISeeAll, PermissionSectionBI
from .view import (
    DataSourceBIAggregations,
    DataSourceBIHostAggregations,
    DataSourceBIHostnameAggregations,
    DataSourceBIHostnameByGroupAggregations,
)


def register(
    data_source_registry: DataSourceRegistry,
    permission_section_registry: PermissionSectionRegistry,
    permission_registry: PermissionRegistry,
) -> None:
    data_source_registry.register(DataSourceBIAggregations)
    data_source_registry.register(DataSourceBIHostAggregations)
    data_source_registry.register(DataSourceBIHostnameAggregations)
    data_source_registry.register(DataSourceBIHostnameByGroupAggregations)

    permission_section_registry.register(PermissionSectionBI)
    permission_registry.register(PermissionBISeeAll)
