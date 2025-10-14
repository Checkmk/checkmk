#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, MutableMapping, Sequence
from enum import StrEnum
from typing import Literal

from pydantic import AliasChoices, BaseModel, Field


class ItemType(StrEnum):
    QUORUM = "quorum"
    LRM = "lrm"
    SERVICE = "service"


class QuorumItem(BaseModel, frozen=True):
    id: str
    node: str
    status: str
    type: Literal["quorum"]


class ServiceItem(BaseModel, frozen=True):
    node: str
    comment: str | None = None
    sid: str
    state: str
    raw_type: Literal["service"] = Field(
        alias="type",
        validation_alias=AliasChoices("type", "raw_type"),
    )

    @property
    def type(self) -> str:
        return self.sid.split(":", 1)[0]


class LrmNode(BaseModel):
    node: str
    status: str
    timestamp: int
    type: Literal["lrm"]
    services: Mapping[str, ServiceItem] = {}

    @property
    def readable_status(self) -> str:
        if "(" not in self.status:
            return self.status
        try:
            after_paren = self.status.split("(", 1)[1]
            return after_paren.split(",", 1)[0].strip()
        except (IndexError, AttributeError):
            return self.status


class SectionHaManagerCurrent(BaseModel, frozen=True):
    quorum: QuorumItem | None = None
    lrm_nodes: Mapping[str, LrmNode]

    @classmethod
    def from_json_list(
        cls, raw_data: Sequence[Mapping[str, str | int]]
    ) -> "SectionHaManagerCurrent":
        quorum = None
        lrm_nodes: MutableMapping[str, LrmNode] = {}
        services_by_node: MutableMapping[str, MutableMapping[str, ServiceItem]] = {}

        for item in raw_data:
            if (t := item.get("type")) == ItemType.QUORUM:
                quorum = QuorumItem.model_validate(item)
            elif t == ItemType.LRM:
                node = str(item["node"])
                lrm_nodes[node] = LrmNode.model_validate(item)
            elif t == ItemType.SERVICE:
                service = ServiceItem.model_validate(item)
                services_by_node.setdefault(service.node, {})[service.sid] = service

        for node, lrm in lrm_nodes.items():
            lrm.services = services_by_node.get(node, {})

        return cls(quorum=quorum, lrm_nodes=lrm_nodes)
