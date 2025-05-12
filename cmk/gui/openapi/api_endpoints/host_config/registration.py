#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.openapi.framework.registry import VersionedEndpointRegistry

from .list_hosts import ENDPOINT_LIST_HOSTS


def register(versioned_endpoint_registry: VersionedEndpointRegistry) -> None:
    versioned_endpoint_registry.register(ENDPOINT_LIST_HOSTS)
