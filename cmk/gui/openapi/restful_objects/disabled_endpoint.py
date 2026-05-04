#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy
from collections.abc import Mapping
from typing import Any

from cmk.gui.http import Response
from cmk.gui.openapi.restful_objects.decorators import WrappedEndpoint
from cmk.gui.openapi.utils import RestAPIForbiddenException


def disabled_legacy(endpoint: WrappedEndpoint, detail: str) -> WrappedEndpoint:
    """Return a copy of the WrappedEndpoint whose handler always raises 403.

    Use this when an endpoint family is part of a feature that is not licensed,
    so callers receive a clear 403 instead of a 404.
    """

    def _stub(_params: Mapping[str, Any]) -> Response:
        raise RestAPIForbiddenException(
            title="Feature not available",
            detail=detail,
        )

    # The WSGI router calls Endpoint.wrapped, not WrappedEndpoint.func, so we must
    # replace wrapped on a copy of the inner Endpoint — not just WrappedEndpoint.func.
    stub_endpoint = copy.copy(endpoint.endpoint)
    stub_endpoint.wrapped = _stub
    return WrappedEndpoint(stub_endpoint, _stub)
