#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.openapi.framework.registry import VersionedEndpointRegistry

from .register_host_via_token import ENDPOINT_REGISTER_HOST_VIA_TOKEN


def register(
    versioned_endpoint_registry: VersionedEndpointRegistry, *, ignore_duplicates: bool
) -> None:
    versioned_endpoint_registry.register(
        ENDPOINT_REGISTER_HOST_VIA_TOKEN, ignore_duplicates=ignore_duplicates
    )
