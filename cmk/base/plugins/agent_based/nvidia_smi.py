#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime
from enum import Enum
from typing import Literal, Mapping
from xml.etree import ElementTree

from pydantic import BaseModel

from .agent_based_api.v1 import get_value_store, register, Service
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.temperature import check_temperature, TempParamType

PowerState = Literal[
    "P0",
    "P1",
    "P2",
    "P3",
    "P4",
    "P5",
    "P6",
    "P7",
    "P8",
    "P9",
    "P10",
    "P11",
    "P12",
    "P13",
    "P14",
    "P15",
]

MiB = 1024.0**2


class PowerManagement(Enum):
    SUPPORTED = "Supported"
    NA = "N/A"


class PowerReadings(BaseModel):
    power_state: PowerState
    power_management: PowerManagement
    power_draw: float | None
    power_limit: float | None
    default_power_limit: float | None
    enforced_power_limit: float | None
    min_power_limit: float | None
    max_power_limit: float | None


class Temperature(BaseModel):
    gpu_temp: float | None
    gpu_temp_max_threshold: float | None
    gpu_temp_slow_threshold: float | None
    gpu_target_temperature: float | None
    memory_temp: float | None
    gpu_temp_max_mem_threshold: float | None


class MemoryUsage(BaseModel):
    total: float | None
    used: float | None
    free: float | None


class MemoryUtilization(BaseModel):
    fb_memory_usage: MemoryUsage
    bar1_memory_usage: MemoryUsage


class Utilization(BaseModel):
    memory_util: MemoryUtilization
    gpu_util: float | None
    encoder_util: float | None
    decoder_util: float | None


class GPU(BaseModel):
    id: str
    product_name: str | None
    product_brand: str | None
    power_readings: PowerReadings
    temperature: Temperature
    utilization: Utilization


class Section(BaseModel):
    timestamp: datetime | None
    driver_version: str | None
    cuda_version: str | None
    attached_gpus: int | None
    gpus: Mapping[str, GPU]


def get_text_from_element(element: ElementTree.Element | None) -> str | None:
    if element is None:
        return None
    return element.text


def get_float_from_element(
    element: ElementTree.Element | None, unit: str, factor: float = 1.0
) -> float | None:
    if not (text_with_unit := get_text_from_element(element)):
        return None
    if text_with_unit == "N/A":
        return None
    if not text_with_unit.endswith(unit):
        return None
    return float(text_with_unit[: -len(unit)]) * factor


def parse_nvidia_smi(string_table: StringTable) -> Section:
    xml = ElementTree.fromstring("".join([element[0] for element in string_table]))
    return Section(
        timestamp=datetime.strptime(timestamp, "%a %b %d %H:%M:%S %Y")
        if (timestamp := get_text_from_element(xml.find("timestamp")))
        else None,
        driver_version=get_text_from_element(xml.find("driver_version")),
        cuda_version=get_text_from_element(xml.find("cuda_version")),
        attached_gpus=get_text_from_element(xml.find("attached_gpus")),
        gpus={
            ":".join(gpu.get("id", "").split(":")[-2:]): GPU(
                id=gpu.get("id"),
                product_name=get_text_from_element(gpu.find("product_name")),
                product_brand=get_text_from_element(gpu.find("product_brand")),
                power_readings=PowerReadings(
                    power_state=get_text_from_element(gpu.find("power_readings/power_state")),
                    power_management=PowerManagement(
                        get_text_from_element(gpu.find("power_readings/power_management"))
                    ),
                    power_draw=get_float_from_element(gpu.find("power_readings/power_draw"), "W"),
                    power_limit=get_float_from_element(gpu.find("power_readings/power_limit"), "W"),
                    default_power_limit=get_float_from_element(
                        gpu.find("power_readings/default_power_limit"), "W"
                    ),
                    enforced_power_limit=get_float_from_element(
                        gpu.find("power_readings/enforced_power_limit"), "W"
                    ),
                    min_power_limit=get_float_from_element(
                        gpu.find("power_readings/min_power_limit"), "W"
                    ),
                    max_power_limit=get_float_from_element(
                        gpu.find("power_readings/max_power_limit"), "W"
                    ),
                ),
                temperature=Temperature(
                    gpu_temp=get_float_from_element(gpu.find("temperature/gpu_temp"), "C"),
                    gpu_temp_max_threshold=get_float_from_element(
                        gpu.find("temperature/gpu_temp_max_threshold"), "C"
                    ),
                    gpu_temp_slow_threshold=get_float_from_element(
                        gpu.find("temperature/gpu_temp_slow_threshold"), "C"
                    ),
                    gpu_target_temperature=get_float_from_element(
                        gpu.find("temperature/gpu_target_temperature"), "C"
                    ),
                    memory_temp=get_float_from_element(gpu.find("temperature/memory_temp"), "C"),
                    gpu_temp_max_mem_threshold=get_float_from_element(
                        gpu.find("temperature/gpu_temp_max_mem_threshold"), "C"
                    ),
                ),
                utilization=Utilization(
                    memory_util=MemoryUtilization(
                        fb_memory_usage=MemoryUsage(
                            total=get_float_from_element(
                                gpu.find("fb_memory_usage/total"), "MiB", MiB
                            ),
                            used=get_float_from_element(
                                gpu.find("fb_memory_usage/used"), "MiB", MiB
                            ),
                            free=get_float_from_element(
                                gpu.find("fb_memory_usage/free"), "MiB", MiB
                            ),
                        ),
                        bar1_memory_usage=MemoryUsage(
                            total=get_float_from_element(
                                gpu.find("bar1_memory_usage/total"), "MiB", MiB
                            ),
                            used=get_float_from_element(
                                gpu.find("bar1_memory_usage/used"), "MiB", MiB
                            ),
                            free=get_float_from_element(
                                gpu.find("bar1_memory_usage/free"), "MiB", MiB
                            ),
                        ),
                    ),
                    gpu_util=get_float_from_element(gpu.find("utilization/gpu_util"), "%"),
                    encoder_util=get_float_from_element(gpu.find("utilization/encoder_util"), "%"),
                    decoder_util=get_float_from_element(gpu.find("utilization/decoder_util"), "%"),
                ),
            )
            for gpu in xml.findall("gpu")
        },
    )


register.agent_section(
    name="nvidia_smi",
    parse_function=parse_nvidia_smi,
)


def discover_nvidia_smi_temperature(section: Section) -> DiscoveryResult:
    for gpu_id, gpu in section.gpus.items():
        if gpu.temperature.gpu_temp is not None:
            yield Service(item=gpu_id)


def check_nvidia_smi_temperature(
    item: str,
    params: TempParamType,
    section: Section,
) -> CheckResult:
    if not (gpu := section.gpus.get(item)):
        return
    if gpu.temperature.gpu_temp is None:
        return
    yield from check_temperature(
        reading=gpu.temperature.gpu_temp,
        params=params,
        unique_name=item,
        value_store=get_value_store(),
    )


register.check_plugin(
    name="nvidia_smi_temperature",
    service_name="Nvidia GPU Temperature %s",
    sections=["nvidia_smi"],
    discovery_function=discover_nvidia_smi_temperature,
    check_ruleset_name="temperature",
    check_default_parameters={},
    check_function=check_nvidia_smi_temperature,
)
