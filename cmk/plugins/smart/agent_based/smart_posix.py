#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

from pydantic import AliasChoices, BaseModel, Field, RootModel

from cmk.agent_based.v2 import (
    AgentSection,
    StringTable,
)


class Temperature(BaseModel, frozen=True):
    current: int
    drive_trip: int | None = None


class SCSIDevice(BaseModel, frozen=True):
    # Not implemented, but needs to be handled in schema
    protocol: Literal["SCSI"]
    name: str


class ATADevice(BaseModel, frozen=True):
    protocol: Literal["ATA"]
    name: str


class NVMeDevice(BaseModel, frozen=True):
    protocol: Literal["NVMe"]
    name: str


class ATARawValue(BaseModel, frozen=True):
    value: int


class ATATableEntry(BaseModel, frozen=True):
    id: int
    name: str
    value: int
    thresh: int
    raw: ATARawValue


class ATATable(BaseModel, frozen=True):
    table: Sequence[ATATableEntry]


class ATAAll(BaseModel, frozen=True):
    device: ATADevice
    model_name: str
    serial_number: str
    ata_smart_attributes: ATATable | None = None
    temperature: Temperature | None = None

    def by_id(self, id_: int) -> ATATableEntry | None:
        if self.ata_smart_attributes is None:
            return None
        for entry in self.ata_smart_attributes.table:
            if entry.id == id_:
                return entry
        return None


class NVMeHealth(BaseModel, frozen=True):
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


class NVMeAll(BaseModel, frozen=True):
    device: NVMeDevice
    model_name: str
    serial_number: str
    nvme_smart_health_information_log: NVMeHealth | None = None


class SCSITemperature(BaseModel, frozen=True):
    # Where this variable is found depends on the smartctl version, either under `temperature` or
    # `scsi_temperature`.
    drive_trip: int


class SCSIAll(BaseModel, frozen=True):
    device: SCSIDevice
    model_name: str = Field(..., validation_alias=AliasChoices("model_name", "scsi_model_name"))
    serial_number: str
    temperature: Temperature | None = None
    scsi_temperature: SCSITemperature | None = None


class SCSIMissingModel(BaseModel, frozen=True):
    # `smartctl` only yields the model name if the vendor identification of the SCSI inquiry
    # starts with "ATA". We don't know why, but we can't discover the disk without the model name.
    # This appears to only happen if `-d scsi` is passed. This means only
    # `<<<smart_posix_scan_arg>>>` is affected and discarding this data is safe.
    device: SCSIDevice
    model_name: None = Field(None, validation_alias=AliasChoices("model_name", "scsi_model_name"))
    serial_number: str


class FailureAll(BaseModel, frozen=True):
    device: None = None  # happens on permission denied.


class SmartctlError(BaseModel, frozen=True):
    # From the `smartctl` code:
    # command line did not parse, or internal error occurred in smartctl (0x01<<0)
    # device open failed (0x01<<1)
    # device is in low power mode and -n option requests to exit (0x01<<1)
    # read device identity (ATA only) failed (0x01<<1)
    # smart command failed, or ATA identify device structure missing information (0x01<<2)

    # If any of the errors above occur, we assume that no SMART data can be collected. We then allow
    # the data to be discarded.
    exit_status: Literal[1, 2, 3, 4, 5, 6, 7]


class CantOpenDevice(BaseModel, frozen=True):
    device: SCSIDevice | ATADevice | NVMeDevice
    smartctl: SmartctlError


@dataclass(frozen=True)
class Section:
    devices: Mapping[str, NVMeAll | ATAAll | SCSIAll]
    failures: Sequence[FailureAll | CantOpenDevice | SCSIMissingModel]


class ParseSection(RootModel):
    root: NVMeAll | ATAAll | SCSIAll | FailureAll | CantOpenDevice | SCSIMissingModel


def parse_smart_posix(string_table: StringTable) -> Section:
    # Each line contains the output of `smartctl --all --json`.
    scans = [ParseSection.model_validate_json(line[0]).root for line in string_table]
    failures: list[FailureAll | CantOpenDevice | SCSIMissingModel] = []
    devices: dict[str, NVMeAll | ATAAll | SCSIAll] = {}
    for scan in scans:
        if isinstance(scan, (FailureAll | CantOpenDevice | SCSIMissingModel)):
            failures.append(scan)
        else:
            devices[f"{scan.model_name} {scan.serial_number}"] = scan
    return Section(devices=devices, failures=failures)


agent_section_smart_posix_all = AgentSection(
    name="smart_posix_all",
    parse_function=parse_smart_posix,
)

agent_section_smart_posix_scan_arg = AgentSection(
    name="smart_posix_scan_arg",
    parse_function=parse_smart_posix,
)
