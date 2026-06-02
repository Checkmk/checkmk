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

from cmk.checkengine.helper_interface import AgentRawData, FetcherError

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
    resource_attribute_filters: Sequence[AttributeFilter]
    scope_attribute_filters: Sequence[AttributeFilter]
    data_point_attribute_filters: Sequence[AttributeFilter]
    check_interval: float

    @classmethod
    def from_serialized(
        cls, metrics_association_raw: str, check_interval: float, host_name: str
    ) -> Self:
        metrics_association = json.loads(metrics_association_raw)

        attribute_filters = metrics_association["attribute_filters"]

        # Manual convenience: a host may carry a single resource attribute key whose value is, by
        # convention, the host's own name (e.g. "service.name"). Expand it into a concrete resource
        # attribute filter so a manually configured host's series can be selected. Hosts created by
        # the DCD connector instead carry the resolved values directly in the attribute filters and
        # leave this empty.
        host_name_filters = (
            [AttributeFilter(key=host_name_resource_attribute_key, value=host_name)]
            if (
                host_name_resource_attribute_key := metrics_association.get(
                    "host_name_resource_attribute_key"
                )
            )
            else []
        )

        return cls(
            resource_attribute_filters=[
                *host_name_filters,
                *(
                    AttributeFilter(key=attribute_filter["key"], value=attribute_filter["value"])
                    for attribute_filter in attribute_filters["resource_attributes"]
                ),
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


def _has_cause(exc: Exception, cause_type: type[Exception]) -> bool:
    while exc.__cause__ is not None:
        _exc = exc.__cause__
        if isinstance(_exc, cause_type):
            return True
    return False


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
        try:
            return AgentRawData(self.make_output(self.omd_root, self.argv).encode("utf-8"))
        except Exception as e:
            if not _has_cause(e, ConnectionRefusedError):
                raise
            else:
                raise FetcherError(
                    "Backend initializing, please wait for 2-3 check cycles. "
                    "If this error persists, make sure the metric backend (Clickhouse) is running. "
                    "If the error still persists, please contact the Checkmk support. "
                    f"(Details: {e})\n"
                ) from e
