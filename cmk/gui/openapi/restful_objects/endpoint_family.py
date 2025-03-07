#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from typing import Dict, List, Optional

from cmk.gui.openapi.restful_objects.type_defs import OpenAPITag


@dataclass
class EndpointFamily:
    """Represents a logical grouping of related REST API endpoints."""

    name: str
    """The name of the endpoint family, used as the tag name in OpenAPI spec."""

    description: str
    """Detailed description of the endpoint family."""

    tag_group: str = "Setup"
    """The tag group this endpoint family belongs to in the OpenAPI spec. The family tag_group can
    be overwritten on an endpoint level"""

    display_name: str | None = None
    """Optional display name, defaults to name if not provided."""

    def to_openapi_tag(self) -> OpenAPITag:
        """Convert this endpoint family to an OpenAPI tag object."""
        tag_obj: OpenAPITag = {
            "name": self.name,
            "x-displayName": self.display_name if self.display_name else self.name,
            "description": self.description,
        }
        return tag_obj


class EndpointFamilyRegistry:
    """Registry for all endpoint families in the REST API."""

    def __init__(self):
        self._families: Dict[str, EndpointFamily] = {}

    def register(self, family: EndpointFamily) -> None:
        if family.name in self._families:
            raise ValueError(f"Endpoint family {family.name} already registered")
        self._families[family.name] = family

    def get(self, name: str) -> Optional[EndpointFamily]:
        return self._families.get(name)

    def get_all(self) -> List[EndpointFamily]:
        return list(self._families.values())


endpoint_family_registry = EndpointFamilyRegistry()
