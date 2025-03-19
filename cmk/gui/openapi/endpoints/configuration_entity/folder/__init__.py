#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Configuration entities / Folder

These endpoints can be used to manipulate folders via the configuration entity API,
for more information see "Configuration entities" endpoints."""

from collections.abc import Mapping
from typing import Any

from cmk.gui.http import Response
from cmk.gui.openapi.endpoints.configuration_entity._common import (
    list_endpoint_decorator,
    serve_configuration_entity_list,
)
from cmk.gui.openapi.restful_objects.registry import EndpointRegistry

from cmk.shared_typing.configuration_entity import ConfigEntityType


@list_endpoint_decorator(ConfigEntityType.folder)
def _list_folder(params: Mapping[str, Any]) -> Response:
    """List existing folder"""
    return serve_configuration_entity_list(ConfigEntityType.folder, params)


def register(endpoint_registry: EndpointRegistry) -> None:
    endpoint_registry.register(_list_folder)
