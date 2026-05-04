#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
import functools
from typing import Any

from cmk.gui.openapi.framework.versioned_endpoint import (
    EndpointBehavior,
    EndpointHandler,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.utils import RestAPIForbiddenException


def disabled_versioned(endpoint: VersionedEndpoint, detail: str) -> VersionedEndpoint:
    """Return a copy of the VersionedEndpoint whose handlers always raise 403.

    Use this when an endpoint family is part of a feature that is not licensed,
    so callers receive a clear 403 instead of a 404.
    """
    stub_versions: dict[Any, EndpointHandler] = {}
    for version, handler in endpoint.versions.items():

        @functools.wraps(handler.handler)
        def _stub(*args: Any, **kwargs: Any) -> Any:  # type: ignore[misc]
            raise RestAPIForbiddenException(
                title="Feature not available",
                detail=detail,
            )

        stub_versions[version] = dataclasses.replace(handler, handler=_stub)
    return dataclasses.replace(
        endpoint,
        versions=stub_versions,
        permissions=EndpointPermissions(),
        behavior=EndpointBehavior(skip_locking=True, update_config_generation=False),
    )
