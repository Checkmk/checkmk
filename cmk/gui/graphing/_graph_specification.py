#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Annotated, final, Literal, override
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import (
    AfterValidator,
    BaseModel,
    computed_field,
    Field,
    field_validator,
    PlainValidator,
    SerializeAsAny,
)
from tzlocal import get_localzone_name

from cmk.ccc.hostaddress import HostName
from cmk.ccc.plugin_registry import Registry
from cmk.gui.utils.roles import UserPermissions

GraphConsolidationFunction = Literal["max", "min", "average"]

AnnotatedHostName = Annotated[HostName, PlainValidator(HostName.parse)]


def validate_time_zone(name: str) -> str:
    """Accept an IANA timezone name, e.g. "Europe/Berlin", as a browser reports it."""
    try:
        ZoneInfo(name)
    except ValueError, ZoneInfoNotFoundError:
        raise ValueError(f"Unknown time zone: {name!r}")
    return name


TimeZoneName = Annotated[str, AfterValidator(validate_time_zone)]


def site_time_zone() -> str:
    """The IANA name of the site's time zone, e.g. "Europe/Berlin"."""
    # tzlocal finds no name when the system has no time zone configured, which is UTC then.
    return get_localzone_name() or "UTC"


@dataclass(frozen=True)
class GraphEnvironment:
    user_permissions: UserPermissions
    debug: bool = False


class GraphSpecification(BaseModel, ABC, frozen=True):
    id: str | None = None

    @staticmethod
    @abstractmethod
    def graph_type_name() -> str: ...

    # mypy does not support other decorators on top of @property:
    # https://github.com/python/mypy/issues/14461
    # https://docs.pydantic.dev/2.0/usage/computed_fields (mypy warning)
    @computed_field  # type: ignore[prop-decorator]
    @property
    @final
    def graph_type(self) -> str:
        return self.graph_type_name()

    def for_storage(self) -> StoredGraphSpecification | None:
        return None


class StoredGraphSpecification(BaseModel, ABC, frozen=True):
    id: str | None

    @staticmethod
    @abstractmethod
    def graph_type_name() -> str: ...

    # mypy does not support other decorators on top of @property:
    # https://github.com/python/mypy/issues/14461
    # https://docs.pydantic.dev/2.0/usage/computed_fields (mypy warning)
    @computed_field  # type: ignore[prop-decorator]
    @property
    @final
    def graph_type(self) -> str:
        return self.graph_type_name()

    @classmethod
    @abstractmethod
    def element_type(cls) -> str: ...


class GraphSpecificationRegistry(Registry[type[GraphSpecification]]):
    @override
    def plugin_name(self, instance: type[GraphSpecification]) -> str:
        return instance.graph_type_name()


graph_specification_registry = GraphSpecificationRegistry()


def parse_graph_specification(graph_specification: object) -> GraphSpecification:
    match graph_specification:
        case GraphSpecification():
            return graph_specification
        case {"graph_type": str(graph_type), **rest}:
            return graph_specification_registry[graph_type].model_validate(rest)
        case dict():
            raise ValueError("Missing 'graph_type' key in graph specification")
        case _:
            raise TypeError(graph_specification)


class GraphExportRequest(BaseModel, frozen=True):
    specification: SerializeAsAny[GraphSpecification]
    consolidation_function: GraphConsolidationFunction = "max"
    time_start: int | None = None
    time_end: int | None = None
    y_range_min: float | None = None
    y_range_max: float | None = None
    # The browser's timezone, which the Vue graph labels its time axis in. The site's one when
    # omitted.
    time_zone: TimeZoneName = Field(default_factory=site_time_zone)

    @field_validator("specification", mode="before")
    @classmethod
    def _parse_specification(cls, value: object) -> GraphSpecification:
        if isinstance(value, GraphSpecification):
            return value
        return parse_graph_specification(value)
