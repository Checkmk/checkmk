#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Annotated, final, Literal, override

from pydantic import (
    BaseModel,
    computed_field,
    field_validator,
    PlainValidator,
    SerializeAsAny,
)

from cmk.ccc.hostaddress import HostName
from cmk.ccc.plugin_registry import Registry
from cmk.gui.utils.roles import UserPermissions

GraphConsolidationFunction = Literal["max", "min", "average"]

AnnotatedHostName = Annotated[HostName, PlainValidator(HostName.parse)]


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

    @classmethod
    def add_visual_type(cls) -> str | None:
        return None


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

    @field_validator("specification", mode="before")
    @classmethod
    def _parse_specification(cls, value: object) -> GraphSpecification:
        if isinstance(value, GraphSpecification):
            return value
        return parse_graph_specification(value)
