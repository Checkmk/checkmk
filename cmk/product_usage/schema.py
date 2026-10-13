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
    count: typing.Annotated[
        int,
        pydantic.Field(
            description="The number of services created by the specific check plug-in across all hosts.",
            examples=[400],
        ),
    ]
    count_hosts: typing.Annotated[
        int,
        pydantic.Field(
            description="The number of unique hosts on which the plug-in is active.",
            examples=[56],
        ),
    ]
    count_disabled: typing.Annotated[
        int,
        pydantic.Field(
            description=(
                "The number of services created by the plug-in that have been disabled via"
                ' "Disabled services" rules (Setup > Services > Service discovery rules >'
                " Disabled services)."
            ),
            examples=[15],
        ),
    ]


class GrafanaUsageData(pydantic.BaseModel):
    is_used: bool = pydantic.Field(
        description="True if Grafana is currently making active requests to the site.",
        examples=[True],
    )
    version: str = pydantic.Field(
        description="The version of Grafana detected via connection headers.",
        examples=["12.3.0"],
    )
    is_grafana_cloud: bool = pydantic.Field(
        description="True if the request originates from a Grafana Cloud instance.",
        examples=[False],
    )


class Metadata(typing.TypedDict):
    version: str
    namespace: str
    name: str


class SelfDescribingModel(pydantic.BaseModel):
    metadata: typing.ClassVar[Metadata]

    def model_dump_with_metadata(self) -> dict[str, object]:
        return {
            "metadata": self.metadata,
            "data": self.model_dump(),
        }

    def model_dump_with_metadata_json(self, indent: int = 0) -> bytes:
        return pydantic_core.to_json(self.model_dump_with_metadata(), indent=indent)

    @classmethod
    def model_json_schema_with_metadata(cls) -> dict[str, object]:
        """JSON schema of the document written by `model_dump_with_metadata`"""
        data_schema = cls.model_json_schema()
        # Hoist the definitions to the root, where the "#/$defs/..." references point to.
        defs = data_schema.pop("$defs", {})
        return {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {
                "metadata": {
                    "type": "object",
                    "properties": {key: {"const": value} for key, value in cls.metadata.items()},
                    "required": list(cls.metadata),
                },
                "data": data_schema,
            },
            "required": ["metadata", "data"],
            "$defs": defs,
        }


class SiteInfo(pydantic.BaseModel):
    id: pydantic.UUID4 = pydantic.Field(
        description=(
            "Random identifier of the site, generated on the first collection."
            " It is not derived from the site name or any other site property."
        ),
        examples=["3f2b8c1e-5a4d-4e7b-9c6f-2d1a0b8e7f53"],
    )
    count_hosts: int = pydantic.Field(
        description="Total number of hosts monitored on the site.",
        examples=[200],
    )
    count_services: int = pydantic.Field(
        description="Total number of services monitored on the site.",
        examples=[4500],
    )
    count_folders: int = pydantic.Field(
        description="The number of folders on the site. Names and paths are never collected.",
        examples=[15],
    )
    edition: str = pydantic.Field(
        description="The specific Checkmk edition in use.",
        examples=["cloud"],
    )
    cmk_version: str = pydantic.Field(
        description=(
            "The version of Checkmk running on the site."
            " This includes the specific build identifier."
        ),
        examples=["2.5.0-2026.01.06"],
    )


class ProductUsageData(SiteInfo):
    timestamp: int = pydantic.Field(
        description="Unix timestamp in seconds of when the data was collected.",
        examples=[1767700800],
    )
    checks: Checks = pydantic.Field(
        description=(
            "These metrics help us understand which features and plug-ins are most valuable to"
            " our users. We collect counts for each plug-in used by the site. The Identifier used"
            " is the technical name/ID of the check command."
        ),
        examples=[{"check_mk-df": {"count": 400, "count_hosts": 56, "count_disabled": 15}}],
    )
    grafana: GrafanaUsageData | None = pydantic.Field(
        default=None,
        description=(
            "This field captures technical details regarding the Grafana plug-in connection."
            " If the site is not connected to the Grafana plug-in, this field returns null."
        ),
        examples=[{"is_used": True, "version": "12.3.0", "is_grafana_cloud": False}],
    )


class ProductUsagePayload(SelfDescribingModel, ProductUsageData):
    metadata: typing.ClassVar[Metadata] = {
        "version": "v1",
        "namespace": "checkmk",
        "name": "product_usage_analytics",
    }
