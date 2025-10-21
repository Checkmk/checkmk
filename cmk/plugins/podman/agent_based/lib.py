#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence
from typing import Literal

from pydantic import AliasPath, BaseModel, Field


class HealthCheckLog(BaseModel, frozen=True):
    output: str = Field(alias="Output")
    exit_code: int = Field(alias="ExitCode")


class ContainerHealth(BaseModel, frozen=True):
    log: Sequence[HealthCheckLog] | None = Field(default=None, alias="Log")
    failing_streak: int = Field(
        alias="FailingStreak",
        description="FailingStreak is the number of consecutive failed healthchecks.",
    )
    status: Literal["starting", "healthy", "unhealthy", ""] = Field(
        alias="Status", description="Status starting, healthy or unhealthy."
    )


class SectionPodmanContainerState(BaseModel, frozen=True):
    status: str = Field(alias="Status")
    started_at: str = Field(alias="StartedAt")
    exit_code: int = Field(alias="ExitCode", description="Exit code of the container.")
    health: ContainerHealth = Field(
        alias="Health",
        description="Describes the results/logs from a healthcheck.",
    )


class ContainerHealthcheck(BaseModel, frozen=True):
    command: Sequence[str] = Field(
        alias="Test",
        description="Test is the test to perform to check that the container is healthy.",
    )


class SectionPodmanContainerConfig(BaseModel, frozen=True):
    healthcheck: ContainerHealthcheck | None = Field(
        default=None,
        alias="Healthcheck",
        description="Health check configuration for the container, if any.",
    )
    healthcheck_on_failure_action: str = Field(
        alias="HealthcheckOnFailureAction",
        description="Action to take when the health check fails.",
    )
    hostname: str = Field(alias="Hostname")
    labels: Mapping[str, str] = Field(alias="Labels")
    user: str = Field(alias="User")


class PodmanContainerNetworkSettings(BaseModel, frozen=True):
    ip_address: str = Field(alias="IPAddress", description="The IP address of the container.")
    gateway: str = Field(alias="Gateway", description="The gateway of the container.")
    mac_address: str = Field(alias="MacAddress", description="The MAC address of the container.")


class SectionPodmanContainerInspect(BaseModel, frozen=True):
    state: SectionPodmanContainerState = Field(alias="State")
    restarts: int = Field(alias="RestartCount", description="Number of restarts of the container.")
    pod: str = Field(alias="Pod", description="The pod this container is part of, if any.")
    config: SectionPodmanContainerConfig = Field(alias="Config")
    network: PodmanContainerNetworkSettings = Field(alias="NetworkSettings")


class SectionPodmanContainerStats(BaseModel, frozen=True):
    cpu_util: float = Field(
        alias="CPU",
        description="CPU utilization of the container expressed in percentages.",
    )
    mem_used: int = Field(alias="MemUsage")
    mem_total: int = Field(alias="MemLimit")
    read_io: int = Field(alias="BlockInput")
    write_io: int = Field(alias="BlockOutput")


class SectionPodmanEngineStats(BaseModel, frozen=True):
    rootless: bool = Field(
        validation_alias=AliasPath("host", "security", "rootless"),
        description="Whether the Podman engine runs in rootless mode.",
    )
    api_version: str = Field(
        validation_alias=AliasPath("version", "APIVersion"),
        description="The API version of the Podman engine.",
    )
    registries: Mapping[str, object]
    hostname: str = Field(
        validation_alias=AliasPath("host", "hostname"),
    )
