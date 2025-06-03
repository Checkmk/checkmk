#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.openapi.framework.registry import VersionedEndpointRegistry

from .create_host import ENDPOINT_CREATE_HOST
from .list_hosts import ENDPOINT_LIST_HOSTS
from .show_host import ENDPOINT_SHOW_HOST


def register(
    versioned_endpoint_registry: VersionedEndpointRegistry, *, ignore_duplicates: bool
) -> None:
    versioned_endpoint_registry.register(ENDPOINT_CREATE_HOST, ignore_duplicates=ignore_duplicates)
    versioned_endpoint_registry.register(ENDPOINT_LIST_HOSTS, ignore_duplicates=ignore_duplicates)
    versioned_endpoint_registry.register(ENDPOINT_SHOW_HOST, ignore_duplicates=ignore_duplicates)
