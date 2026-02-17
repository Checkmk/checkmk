#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal, TypeVar

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    FixedLevelsT,
    NoLevelsT,
    render,
    Service,
    StringTable,
)

type Params = Mapping[str, ItemParams]

type ItemParams = Mapping[
    Literal["size_upper", "reclaimable_upper", "total", "active"],
    NoLevelsT | FixedLevelsT[int],
]


@dataclass(frozen=True, kw_only=True)
class Entity:
    id: str
    size: float
    active: bool
    reclaimable_size: float | None = None
    creation: str | int | None = None
    repository: str | None = None
    tag: str | None = None
    containers: int | None = None


@dataclass(frozen=True, kw_only=True)
class EntityGroup:
    items: Sequence[Entity]

    def total_size(self) -> float:
        return sum(e.size for e in self.items)

    def active_count(self) -> int:
        return sum(e.active for e in self.items)

    def total_reclaimable_size(self) -> float:
        return sum(e.reclaimable_size for e in self.items if e.reclaimable_size is not None)


@dataclass(frozen=True, kw_only=True)
class DiskUsage:
    size: float
    reclaimable_size: float | None = None
    total_number: int
    active_number: int


@dataclass(frozen=True, kw_only=True)
class Section:
    images: EntityGroup
    disk_usage: Mapping[str, DiskUsage]


T = TypeVar("T")

_SUMMARY_TYPE_MAP = {
    "Images": "images",
    "Containers": "containers",
    "Local Volumes": "volumes",
}


def _is_summary_format(string_table: StringTable) -> bool:
    if not string_table:
        return False
    data = json.loads(string_table[0][0])
    if isinstance(data, list) and data and "Type" in data[0]:
        return True
    return False


def _aggregate_disk_usage(existing: DiskUsage | None, new: DiskUsage) -> DiskUsage:
    if existing is None:
        return new

    return DiskUsage(
        size=existing.size + new.size,
        reclaimable_size=(
            (existing.reclaimable_size or 0) + (new.reclaimable_size or 0)
            if existing.reclaimable_size is not None or new.reclaimable_size is not None
            else None
        ),
        total_number=existing.total_number + new.total_number,
        active_number=existing.active_number + new.active_number,
    )


def _parse_summary_format(string_table: StringTable) -> Mapping[str, DiskUsage]:
    aggregated: dict[str, DiskUsage] = {}
    for line in string_table:
        data = json.loads(line[0])
        entries = data if isinstance(data, list) else [data]
        for entry in entries:
            if not (type_key := _SUMMARY_TYPE_MAP.get(entry.get("Type"))):
                continue
            usage = DiskUsage(
                size=float(entry.get("RawSize", 0)),
                reclaimable_size=float(entry.get("RawReclaimable", 0)),
                total_number=int(entry.get("Total", 0)),
                active_number=int(entry.get("Active", 0)),
            )
            aggregated[type_key] = _aggregate_disk_usage(aggregated.get(type_key), usage)
    return aggregated


def parse_entities(
    string_table: StringTable,
    key: str,
    factory: Callable[[dict[str, Any]], T],
) -> list[T]:
    result = []
    for line in string_table:
        data = json.loads(line[0])
        entries = data.get(key, []) if isinstance(data, dict) else data
        for entry in entries:
            result.append(factory(entry))
    return result


def pre_parse_podman_disk_usage(
    string_table: StringTable,
) -> tuple[EntityGroup, EntityGroup, EntityGroup]:
    containers = parse_entities(
        string_table,
        "Containers",
        lambda c: Entity(
            id=c.get("ContainerID", ""),
            size=float(c.get("Size", 0)),
            reclaimable_size=float(c.get("RWSize", 0)),
            active=c.get("Status", "").lower() == "running",
        ),
    )
    images = parse_entities(
        string_table,
        "Images",
        lambda i: Entity(
            id=i.get("ImageID", ""),
            size=float(i.get("Size", 0)),
            active=int(i.get("Containers", 0)) > 0,
            repository=i.get("Repository", ""),
            tag=i.get("Tag", ""),
            containers=int(i.get("Containers", 0)),
            creation=i.get("Created"),
        ),
    )
    volumes = parse_entities(
        string_table,
        "Volumes",
        lambda i: Entity(
            id=i.get("VolumeName", ""),
            size=float(i.get("Size", 0)),
            reclaimable_size=float(i.get("ReclaimableSize", 0)),
            active=int(i.get("Links", 0)) > 0,
        ),
    )
    return EntityGroup(items=containers), EntityGroup(items=images), EntityGroup(items=volumes)


def parse_podman_disk_usage(string_table: StringTable) -> Section:
    if _is_summary_format(string_table):
        # If the summary format (CLI command output) is detected, we parse it directly
        # into DiskUsage objects without trying to extract individual entities.
        disk_usage = _parse_summary_format(string_table)
        return Section(
            images=EntityGroup(items=[]),
            disk_usage=disk_usage,
        )

    containers, images, volumes = pre_parse_podman_disk_usage(string_table)
    return Section(
        images=images,
        disk_usage={
            "containers": DiskUsage(
                size=containers.total_size(),
                reclaimable_size=containers.total_reclaimable_size(),
                total_number=len(containers.items),
                active_number=containers.active_count(),
            ),
            "images": DiskUsage(
                size=images.total_size(),
                total_number=len(images.items),
                active_number=images.active_count(),
            ),
            "volumes": DiskUsage(
                size=volumes.total_size(),
                reclaimable_size=volumes.total_reclaimable_size(),
                total_number=len(volumes.items),
                active_number=volumes.active_count(),
            ),
        },
    )


agent_section_podman_disk_usage: AgentSection = AgentSection(
    name="podman_disk_usage", parse_function=parse_podman_disk_usage
)


def discover_podman_disk_usage(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section.disk_usage)


def _check_podman_disk_usage(item: str, params: ItemParams, section: DiskUsage) -> CheckResult:
    yield from check_levels(
        value=section.size,
        levels_upper=params.get("size_upper"),
        label="Size",
        render_func=render.bytes,
        metric_name=f"podman_disk_usage_{item}_total_size",
        boundaries=(0, section.size),
    )
    if section.reclaimable_size is not None:
        yield from check_levels(
            value=section.reclaimable_size,
            levels_upper=params.get("reclaimable_upper"),
            label="Reclaimable",
            render_func=render.bytes,
            metric_name=f"podman_disk_usage_{item}_reclaimable_size",
        )
    yield from check_levels(
        value=section.total_number,
        levels_upper=params.get("total"),
        label="Total",
        notice_only=True,
        metric_name=f"podman_disk_usage_{item}_total_number",
        render_func=lambda x: f"{int(x)}",
    )
    yield from check_levels(
        value=section.active_number,
        levels_upper=params.get("active"),
        label="Active",
        notice_only=True,
        metric_name=f"podman_disk_usage_{item}_active_number",
        render_func=lambda x: f"{int(x)}",
    )


def check_podman_disk_usage(item: str, params: Params, section: Section) -> CheckResult:
    if (data := section.disk_usage.get(item)) is None:
        return

    yield from _check_podman_disk_usage(item, params.get(item, {}), data)


check_plugin_podman_disk_usage = CheckPlugin(
    name="podman_disk_usage",
    service_name="Podman disk usage: %s",
    discovery_function=discover_podman_disk_usage,
    check_function=check_podman_disk_usage,
    check_ruleset_name="podman_disk_usage",
    check_default_parameters={},
)
