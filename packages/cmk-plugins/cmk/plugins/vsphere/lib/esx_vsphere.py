#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import enum
from collections import OrderedDict
from collections.abc import Mapping, Sequence
from typing import Any, Final

from pydantic import BaseModel, ConfigDict

Section = OrderedDict[str, Any]

CounterValues = Sequence[str]
SubSectionCounter = Mapping[str, list[tuple[CounterValues, str]]]
SectionCounter = Mapping[str, SubSectionCounter]


class ESXMemory(BaseModel, frozen=True):
    """ESX VSphere VM memory model
    host_usage:
        consumed host memory
    guest_usage:
        active guest memory
    ballooned:
        size of the balloon driver in the VM
    shared:
        the portion of memory, in MB, that is granted to this VM from non-shared memory
        (must not be set)
    private:
        the portion of memory, in MB, that is granted to this VM from host memory that is shared
        between VMs; only present if the VM data is collected via vCenter, in case the data is
        collected directly from an esx host, this value will be None
    """

    host_usage: float
    guest_usage: float
    ballooned: float
    shared: float
    private: float | None


class ESXCpu(BaseModel):
    """ESX VSphere VM cpu model

    overall_usage:
        overall cpu usage in Mhz
    cpus_count:
        count of virtual CPUs
    cores_per_socket:
        number of cores per socket
    """

    model_config = ConfigDict(frozen=True)

    overall_usage: int
    cpus_count: int
    cores_per_socket: int


class ESXDataStore(BaseModel):
    name: str
    free_space: float
    capacity: float


class ESXStatus(enum.Enum):
    guestToolsCurrent = "guestToolsCurrent"
    guestToolsNeedUpgrade = "guestToolsNeedUpgrade"
    guestToolsNotInstalled = "guestToolsNotInstalled"
    guestToolsUnmanaged = "guestToolsUnmanaged"


class HeartBeatStatus(enum.Enum):
    GRAY = "GRAY"
    GREEN = "GREEN"
    RED = "RED"
    YELLOW = "YELLOW"
    UNKNOWN = "UNKNOWN"


class HeartBeat(BaseModel):
    status: HeartBeatStatus
    value: str


class SectionESXVm(BaseModel):
    model_config = ConfigDict(frozen=True)

    mounted_devices: Sequence[str]
    snapshots: Sequence[str]
    status: ESXStatus | None
    power_state: str | None
    memory: ESXMemory | None
    cpu: ESXCpu | None
    datastores: Sequence[ESXDataStore] | None
    heartbeat: HeartBeat | None
    host: str | None
    name: str | None
    systime: str | None


def average_parsed_data(values: CounterValues) -> float:
    """
    >>> average_parsed_data(['1', '2'])
    1.5
    >>> average_parsed_data(['1'])
    1.0
    >>> average_parsed_data([])
    0
    """
    return sum(map(int, values)) / len(values) if values else 0


# VMware vSphere reports -1 when a metric could not be collected for a given sample interval.
# See: https://github.com/vmware/pyvmomi/issues/191#issuecomment-72217028
ESX_COUNTER_UNAVAILABLE: Final = "-1"


def average_valid_samples(values: CounterValues) -> float | None:
    """Average counter samples, excluding unavailable (-1) values.

    Returns None when every sample in the window is unavailable, so callers
    can omit the metric entirely rather than reporting a misleading zero.
    Use for rate metrics (throughput, IOPS).
    """
    valid = [v for v in values if v != ESX_COUNTER_UNAVAILABLE]
    return average_parsed_data(valid) if valid else None


def max_valid_sample(values: CounterValues) -> int | None:
    """Return the maximum counter sample, excluding unavailable (-1) values.

    Returns None when every sample is unavailable.
    Use for latency metrics where the worst-case observed value is reported.
    """
    valid = [int(v) for v in values if v != ESX_COUNTER_UNAVAILABLE]
    return max(valid) if valid else None


def last_valid_sample(values: CounterValues) -> str | None:
    """Return the most-recent valid counter sample, excluding unavailable (-1) values.

    Returns None when every sample is unavailable.
    Use for monotonic counters (uptime) and current-state metrics (memory usage)
    where only the most recent reading is meaningful.
    """
    for v in reversed(values):
        if v != ESX_COUNTER_UNAVAILABLE:
            return v
    return None
