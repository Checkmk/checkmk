#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Sequence
from dataclasses import dataclass

__all__ = ["MetricBackendFetcherConfig"]

from enum import Enum
from typing import Self


class AttributeType(Enum):
    SCOPE = "scope"
    RESOURCE = "resource"
    DATA_POINT = "data_point"


@dataclass(frozen=True)
class AttributeFilter:
    attribute_type: AttributeType
    attribute_key: str
    attribute_value: str


@dataclass(frozen=True)
class MetricBackendFetcherConfig:
    host_name_resource_attribute_key: str
    attribute_filters: Sequence[AttributeFilter]

    @classmethod
    def from_serialized(cls, metrics_association_raw: str) -> Self:
        metrics_association = json.loads(metrics_association_raw)

        host_name_resource_attribute_key = metrics_association["host_name_resource_attribute_key"]

        filter_args = [
            AttributeFilter(
                attribute_type=AttributeType(f["attribute_type"]),
                attribute_key=f["attribute_key"],
                attribute_value=f["attribute_value"],
            )
            for f in metrics_association["attribute_filters"]
        ]

        return cls(
            host_name_resource_attribute_key=host_name_resource_attribute_key,
            attribute_filters=filter_args,
        )
