#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import Literal

import pydantic

from cmk.agent_based.v2 import (
    AgentSection,
    StringTable,
)


class Temperature(pydantic.BaseModel, frozen=True):
    current: int


class SCSIDevice(pydantic.BaseModel, frozen=True):
    # Not implemented, but needs to be handled in schema
    protocol: Literal["SCSI"]
    name: str


class ATADevice(pydantic.BaseModel, frozen=True):
    protocol: Literal["ATA"]
    name: str


class NVMeDevice(pydantic.BaseModel, frozen=True):
    protocol: Literal["NVMe"]
    name: str


class ATARawValue(pydantic.BaseModel, frozen=True):
    value: int


class ATATableEntry(pydantic.BaseModel, frozen=True):
    id: int
    name: str
    value: int
    thresh: int
    raw: ATARawValue


class ATATable(pydantic.BaseModel, frozen=True):
    table: Sequence[ATATableEntry]


class ATAAll(pydantic.BaseModel, frozen=True):
    device: ATADevice
    ata_smart_attributes: ATATable | None = None
    temperature: Temperature | None = None

    def by_id(self, id_: int) -> ATATableEntry | None:
        if self.ata_smart_attributes is None:
            return None
        for entry in self.ata_smart_attributes.table:
            if entry.id == id_:
                return entry
        return None


class NVMeHealth(pydantic.BaseModel, frozen=True):
    power_on_hours: int
    power_cycles: int
    critical_warning: int
    media_errors: int
    available_spare: int
    available_spare_threshold: int
    temperature: int | None = None
    percentage_used: int
    num_err_log_entries: int
    data_units_read: int
    data_units_written: int


class NVMeAll(pydantic.BaseModel, frozen=True):
    device: NVMeDevice
    nvme_smart_health_information_log: NVMeHealth | None = None


class SCSIAll(pydantic.BaseModel, frozen=True):
    device: SCSIDevice
    temperature: Temperature | None = None


class FailureAll(pydantic.BaseModel, frozen=True):
    device: None = None  # happens on permission denied.


Section = Sequence[NVMeAll | ATAAll | SCSIAll | FailureAll]


class ParseSection(pydantic.RootModel):
    root: NVMeAll | ATAAll | SCSIAll | FailureAll


def parse_smart_posix_all(string_table: StringTable) -> Section:
    # Each line contains the output of `smartctl --all --json`.
    return [ParseSection.model_validate_json(line[0]).root for line in string_table]


agent_section_smart_posix_all = AgentSection(
    name="smart_posix_all",
    parse_function=parse_smart_posix_all,
)
