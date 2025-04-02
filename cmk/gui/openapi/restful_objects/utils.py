#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.http import HTTPMethod


def endpoint_ident(method: HTTPMethod, route_path: str, content_type: str) -> str:
    """Provide an identity for an endpoint

    This can be used for keys in a dictionary, e.g. the ENDPOINT_REGISTRY."""
    return f"{method}:{route_path}:{content_type}"
