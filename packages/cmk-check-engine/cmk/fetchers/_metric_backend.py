#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import logging
import typing
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Final, Self

from cmk.helper_interface import AgentRawData

from ._abstract import Fetcher


class AttributeType(Enum):
    SCOPE = "scope"
    RESOURCE = "resource"
    DATA_POINT = "data_point"


@dataclass(frozen=True)
class AttributeFilter:
    key: str
    value: str


@dataclass(frozen=True)
class MetricBackendFetcherConfig:
    host_name_resource_attribute_key: str
    resource_attribute_filters: Sequence[AttributeFilter]
    scope_attribute_filters: Sequence[AttributeFilter]
    data_point_attribute_filters: Sequence[AttributeFilter]
    check_interval: float

    @classmethod
    def from_serialized(cls, metrics_association_raw: str, check_interval: float) -> Self:
        metrics_association = json.loads(metrics_association_raw)

        host_name_resource_attribute_key = metrics_association["host_name_resource_attribute_key"]
        attribute_filters = metrics_association["attribute_filters"]

        return cls(
            host_name_resource_attribute_key=host_name_resource_attribute_key,
            resource_attribute_filters=[
                AttributeFilter(key=attribute_filter["key"], value=attribute_filter["value"])
                for attribute_filter in attribute_filters["resource_attributes"]
            ],
            scope_attribute_filters=[
                AttributeFilter(key=attribute_filter["key"], value=attribute_filter["value"])
                for attribute_filter in attribute_filters["scope_attributes"]
            ],
            data_point_attribute_filters=[
                AttributeFilter(key=attribute_filter["key"], value=attribute_filter["value"])
                for attribute_filter in attribute_filters["data_point_attributes"]
            ],
            check_interval=check_interval,
        )


class MetricBackendFetcher(Fetcher[AgentRawData]):
    def __init__(
        self,
        *,
        argv: Sequence[str],
        make_output: Callable[[Path, Sequence[str]], str],
        omd_root: Path,
    ) -> None:
        super().__init__()
        self.argv: Final = argv
        self.make_output = make_output
        self.omd_root = omd_root
        self._logger: Final = logging.getLogger("cmk.helper.metric_backend_fetcher")

    def __repr__(self) -> str:
        return f"{type(self).__name__}(" + ", ".join((f"argv={self.argv!r}",)) + ")"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MetricBackendFetcher):
            return False
        return self.argv == other.argv

    def open(self) -> None:
        pass

    def close(self) -> None:
        pass

    @typing.override
    def _fetch_from_io(self, mode: object) -> AgentRawData:
        self._logger.debug("Get data from metric backend")

        return AgentRawData(self.make_output(self.omd_root, self.argv).encode("utf-8"))
