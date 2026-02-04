#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import typing
from uuid import UUID

import pydantic
import pydantic_core

type Checks = dict[str, CheckData]

ProductUsageSiteId = typing.NewType("ProductUsageSiteId", UUID)


class CheckData(typing.TypedDict):
    count: int
    count_hosts: int
    count_disabled: int


class GrafanaUsageData(pydantic.BaseModel):
    is_used: bool
    version: str
    is_grafana_cloud: bool


class Metadata(typing.TypedDict):
    version: str
    namespace: str
    name: str


class SelfDescribingModel(pydantic.BaseModel):
    __version__: str
    __namespace__: str
    __name__: str

    def model_dump_with_metadata(self) -> dict[str, typing.Any]:
        return {
            "metadata": self._metadata(),
            "data": self.model_dump(),
        }

    def _metadata(self) -> Metadata:
        return {
            "version": self.__version__,
            "namespace": self.__namespace__,
            "name": self.__name__,
        }

    def model_dump_with_metadata_json(self, indent: int = 0) -> bytes:
        return pydantic_core.to_json(self.model_dump_with_metadata(), indent=indent)


class SiteInfo(pydantic.BaseModel):
    id: pydantic.UUID4
    count_hosts: int
    count_services: int
    count_folders: int
    edition: str
    cmk_version: str


class ProductUsageData(SiteInfo):
    timestamp: int
    checks: Checks
    grafana: GrafanaUsageData | None = None


class ProductUsagePayload(SelfDescribingModel, ProductUsageData):
    __version__: str = "v1"
    __namespace__: str = "checkmk"
    __name__: str = "product_usage_analytics"
