#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="comparison-overlap"

from collections.abc import Mapping
from datetime import datetime
from enum import Enum
from typing import cast, Literal, TypedDict
from xml.etree import ElementTree

from pydantic import BaseModel

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Metric,
    render,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.lib.memory import check_element
from cmk.plugins.lib.temperature import check_temperature, TempParamType

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
    "Requested functionality has been deprecated",
]

MiB = 1024.0**2
MHz_to_Hz_factor = 1000_000


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


class Clock(BaseModel):
    graphics_clock: float | None
    sm_clock: float | None
    mem_clock: float | None
    video_clock: float | None
    graphics_clock_max: float | None
    sm_clock_max: float | None
    mem_clock_max: float | None
    video_clock_max: float | None


class GPU(BaseModel):
    id: str
    product_name: str | None
    product_brand: str | None
    power_readings: PowerReadings
    temperature: Temperature
    utilization: Utilization
    clock: Clock


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


def get_int_from_element(element: ElementTree.Element | None) -> int | None:
    if element is None or element.text is None:
        return None
    return int(element.text)


def _let_pydantic_check_none[T](value: T | None) -> T:
    return cast(T, value)


def _let_pydantic_check_power_state(value: str | None) -> PowerState:
    return cast(PowerState, value)


def parse_nvidia_smi(string_table: StringTable) -> Section:
    xml = ElementTree.fromstring("".join([element[0] for element in string_table]))
    # find the element name for power_readings
    power_readings_element = "gpu_power_readings"
    if xml.find(f"gpu/{power_readings_element}") is None:
        power_readings_element = "power_readings"
    gpu_power_draw_element = "average_power_draw"
    if xml.find(f"gpu/{power_readings_element}/{gpu_power_draw_element}") is None:
        gpu_power_draw_element = "power_draw"
    gpu_power_limit_element = "current_power_limit"
    if xml.find(f"gpu/{power_readings_element}/{gpu_power_limit_element}") is None:
        gpu_power_limit_element = "power_limit"
    has_power_management = xml.find(f"gpu/{power_readings_element}/power_management") is not None
    return Section(
        timestamp=(
            datetime.strptime(timestamp, "%a %b %d %H:%M:%S %Y")
            if (timestamp := get_text_from_element(xml.find("timestamp")))
            else None
        ),
        driver_version=get_text_from_element(xml.find("driver_version")),
        cuda_version=get_text_from_element(xml.find("cuda_version")),
        attached_gpus=get_int_from_element(xml.find("attached_gpus")),
        gpus={
            gpu.get("id", ""): GPU(
                id=_let_pydantic_check_none(gpu.get("id")),
                product_name=get_text_from_element(gpu.find("product_name")),
                product_brand=get_text_from_element(gpu.find("product_brand")),
                power_readings=PowerReadings(
                    power_state=_let_pydantic_check_power_state(
                        get_text_from_element(gpu.find(f"{power_readings_element}/power_state"))
                    ),
                    power_management=(
                        PowerManagement(
                            get_text_from_element(
                                gpu.find(f"{power_readings_element}/power_management")
                            )
                        )
                        if has_power_management
                        # assume power management is supported because newer versions of the xml don't contain it anymore
                        else PowerManagement.SUPPORTED
                    ),
                    power_draw=get_float_from_element(
                        gpu.find(f"{power_readings_element}/{gpu_power_draw_element}"), "W"
                    ),
                    power_limit=get_float_from_element(
                        gpu.find(f"{power_readings_element}/{gpu_power_limit_element}"), "W"
                    ),
                    default_power_limit=get_float_from_element(
                        gpu.find(f"{power_readings_element}/default_power_limit"), "W"
                    ),
                    enforced_power_limit=get_float_from_element(
                        gpu.find(f"{power_readings_element}/enforced_power_limit"), "W"
                    ),
                    min_power_limit=get_float_from_element(
                        gpu.find(f"{power_readings_element}/min_power_limit"), "W"
                    ),
                    max_power_limit=get_float_from_element(
                        gpu.find(f"{power_readings_element}/max_power_limit"), "W"
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
                clock=Clock(
                    graphics_clock=get_float_from_element(gpu.find("clocks/graphics_clock"), "MHz"),
                    sm_clock=get_float_from_element(gpu.find("clocks/sm_clock"), "MHz"),
                    mem_clock=get_float_from_element(gpu.find("clocks/mem_clock"), "MHz"),
                    video_clock=get_float_from_element(gpu.find("clocks/video_clock"), "MHz"),
                    graphics_clock_max=get_float_from_element(
                        gpu.find("max_clocks/graphics_clock"), "MHz"
                    ),
                    sm_clock_max=get_float_from_element(gpu.find("max_clocks/sm_clock"), "MHz"),
                    mem_clock_max=get_float_from_element(gpu.find("max_clocks/mem_clock"), "MHz"),
                    video_clock_max=get_float_from_element(
                        gpu.find("max_clocks/video_clock"), "MHz"
                    ),
                ),
            )
            for gpu in xml.findall("gpu")
        },
    )


agent_section_nvidia_smi = AgentSection(
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


check_plugin_nvidia_smi_temperature = CheckPlugin(
    name="nvidia_smi_temperature",
    service_name="Nvidia GPU Temperature %s",
    sections=["nvidia_smi"],
    discovery_function=discover_nvidia_smi_temperature,
    check_ruleset_name="temperature",
    check_default_parameters={},
    check_function=check_nvidia_smi_temperature,
)


def discover_nvidia_smi_gpu_util(section: Section) -> DiscoveryResult:
    for gpu_id, gpu in section.gpus.items():
        if gpu.utilization.gpu_util is not None:
            yield Service(item=gpu_id)


class GenericLevelsParam(TypedDict):
    levels: tuple[float, float] | None


def check_nvidia_smi_gpu_util(
    item: str,
    params: GenericLevelsParam,
    section: Section,
) -> CheckResult:
    if not (gpu := section.gpus.get(item)):
        return
    if gpu.utilization.gpu_util is None:
        return
    yield from check_levels_v1(
        gpu.utilization.gpu_util,
        levels_upper=params.get("levels"),
        render_func=render.percent,
        metric_name="gpu_utilization",
        label="Utilization",
    )


check_plugin_nvidia_smi_gpu_util = CheckPlugin(
    name="nvidia_smi_gpu_util",
    service_name="Nvidia GPU utilization %s",
    sections=["nvidia_smi"],
    discovery_function=discover_nvidia_smi_gpu_util,
    check_ruleset_name="nvidia_smi_gpu_util",
    check_default_parameters=GenericLevelsParam(levels=None),
    check_function=check_nvidia_smi_gpu_util,
)


def discover_nvidia_smi_en_de_coder_util(section: Section) -> DiscoveryResult:
    for gpu_id, gpu in section.gpus.items():
        if gpu.utilization.encoder_util is not None or gpu.utilization.decoder_util is not None:
            yield Service(item=gpu_id)


class DeEnCoderParams(TypedDict):
    encoder_levels: tuple[float, float] | None
    decoder_levels: tuple[float, float] | None


def check_nvidia_smi_en_de_coder_util(
    item: str,
    params: DeEnCoderParams,
    section: Section,
) -> CheckResult:
    if not (gpu := section.gpus.get(item)):
        return
    if gpu.utilization.encoder_util is not None:
        yield from check_levels_v1(
            gpu.utilization.encoder_util,
            levels_upper=params.get("encoder_levels"),
            render_func=render.percent,
            metric_name="encoder_utilization",
            label="Encoder",
        )
    if gpu.utilization.decoder_util is not None:
        yield from check_levels_v1(
            gpu.utilization.decoder_util,
            levels_upper=params.get("decoder_levels"),
            render_func=render.percent,
            metric_name="decoder_utilization",
            label="Decoder",
        )


check_plugin_nvidia_smi_en_de_coder_util = CheckPlugin(
    name="nvidia_smi_en_de_coder_util",
    service_name="Nvidia GPU En-/Decoder utilization %s",
    sections=["nvidia_smi"],
    discovery_function=discover_nvidia_smi_en_de_coder_util,
    check_ruleset_name="nvidia_smi_en_de_coder_util",
    check_default_parameters=DeEnCoderParams(encoder_levels=None, decoder_levels=None),
    check_function=check_nvidia_smi_en_de_coder_util,
)


def discover_nvidia_smi_power(section: Section) -> DiscoveryResult:
    for gpu_id, gpu in section.gpus.items():
        if gpu.power_readings.power_management == PowerManagement.SUPPORTED:
            yield Service(item=gpu_id)


def check_nvidia_smi_power(
    item: str,
    params: GenericLevelsParam,
    section: Section,
) -> CheckResult:
    if (gpu := section.gpus.get(item)) is None or gpu.power_readings is None:
        return

    if gpu.power_readings.power_draw is not None:
        power_limit = gpu.power_readings.power_limit
        yield from check_levels_v1(
            gpu.power_readings.power_draw,
            levels_upper=params.get(
                "levels", None if power_limit is None else (power_limit, power_limit)
            ),
            render_func=lambda x: "%.2f W" % x,
            metric_name="power_usage",
            boundaries=(0.0, power_limit),
            label="Power Draw",
        )
    yield Result(
        state=State.OK,
        notice=f"Power limit: {gpu.power_readings.power_limit} W",
    )
    yield Result(
        state=State.OK,
        notice=f"Min power limit: {gpu.power_readings.min_power_limit} W",
    )
    yield Result(
        state=State.OK,
        notice=f"Max power limit: {gpu.power_readings.max_power_limit} W",
    )


check_plugin_nvidia_smi_power = CheckPlugin(
    name="nvidia_smi_power",
    service_name="Nvidia GPU Power %s",
    sections=["nvidia_smi"],
    discovery_function=discover_nvidia_smi_power,
    check_ruleset_name="nvidia_smi_power",
    check_default_parameters=GenericLevelsParam(levels=None),
    check_function=check_nvidia_smi_power,
)


class MemoryParams(TypedDict):
    levels_total: tuple[float, float] | None
    levels_bar1: tuple[float, float] | None
    levels_fb: tuple[float, float] | None


def discover_nvidia_smi_memory_util(section: Section) -> DiscoveryResult:
    for gpu_id, gpu in section.gpus.items():
        if gpu.utilization.memory_util is not None:
            yield Service(item=gpu_id)


def check_nvidia_smi_memory_util(
    item: str,
    params: MemoryParams,
    section: Section,
) -> CheckResult:
    if not (gpu := section.gpus.get(item)):
        return

    fb_mem_usage_total = gpu.utilization.memory_util.fb_memory_usage.total
    fb_mem_usage_free = gpu.utilization.memory_util.fb_memory_usage.free
    fb_mem_usage_used = gpu.utilization.memory_util.fb_memory_usage.used

    bar1_mem_usage_total = gpu.utilization.memory_util.bar1_memory_usage.total
    bar1_mem_usage_free = gpu.utilization.memory_util.bar1_memory_usage.free
    bar1_mem_usage_used = gpu.utilization.memory_util.bar1_memory_usage.used

    if (
        fb_mem_usage_total is not None
        and fb_mem_usage_used is not None
        and bar1_mem_usage_total is not None
        and bar1_mem_usage_used is not None
    ):
        sum_total = fb_mem_usage_total + bar1_mem_usage_total
        sum_used = fb_mem_usage_used + bar1_mem_usage_used
        levels_total = params.get("levels_total")
        yield from check_element(
            label="Total memory",
            used=sum_used,
            total=sum_total,
            levels=(
                "perc_used",
                (levels_total[0], levels_total[1]) if levels_total is not None else (None, None),
            ),
            create_percent_metric=True,
        )

    if fb_mem_usage_used is not None and fb_mem_usage_total is not None and fb_mem_usage_free:
        levels_fb = params.get("levels_fb")
        yield from check_element(
            label="FB memory",
            used=fb_mem_usage_used,
            total=fb_mem_usage_total,
            levels=(
                "perc_used",
                (levels_fb[0], levels_fb[1]) if levels_fb is not None else (None, None),
            ),
            metric_name="fb_mem_usage_used",
        )
        yield Metric("fb_mem_usage_free", fb_mem_usage_free, boundaries=(0, fb_mem_usage_total))
        yield Metric("fb_mem_usage_total", fb_mem_usage_total)

    if bar1_mem_usage_used is not None and bar1_mem_usage_total is not None and bar1_mem_usage_free:
        levels_bar1 = params.get("levels_bar1")
        yield from check_element(
            label="BAR1 memory",
            used=bar1_mem_usage_used,
            total=bar1_mem_usage_total,
            levels=(
                "perc_used",
                (levels_bar1[0], levels_bar1[1]) if levels_bar1 is not None else (None, None),
            ),
            metric_name="bar1_mem_usage_used",
        )
        yield Metric(
            "bar1_mem_usage_free",
            bar1_mem_usage_free,
            boundaries=(0, bar1_mem_usage_total),
        )
        yield Metric("bar1_mem_usage_total", bar1_mem_usage_total)


check_plugin_nvidia_smi_memory_util = CheckPlugin(
    name="nvidia_smi_memory_util",
    service_name="Nvidia GPU Memory utilization %s",
    sections=["nvidia_smi"],
    discovery_function=discover_nvidia_smi_memory_util,
    check_ruleset_name="nvidia_smi_memory_util",
    check_default_parameters=MemoryParams(levels_total=None, levels_bar1=None, levels_fb=None),
    check_function=check_nvidia_smi_memory_util,
)


class ClockParams(TypedDict):
    levels_graphics_upper: tuple[float, float] | None
    levels_graphics_lower: tuple[float, float] | None
    levels_sm_upper: tuple[float, float] | None
    levels_sm_lower: tuple[float, float] | None
    levels_mem_upper: tuple[float, float] | None
    levels_mem_lower: tuple[float, float] | None
    levels_video_upper: tuple[float, float] | None
    levels_video_lower: tuple[float, float] | None


def discover_nvidia_smi_clock_speed(section: Section) -> DiscoveryResult:
    for gpu_id, gpu in section.gpus.items():
        if gpu.clock.graphics_clock is not None:
            yield Service(item=gpu_id)


def check_nvidia_smi_clock_speed(
    item: str,
    params: ClockParams,
    section: Section,
) -> CheckResult:
    if not (gpu := section.gpus.get(item)):
        return

    graphics_clock = gpu.clock.graphics_clock
    sm_clock = gpu.clock.sm_clock
    mem_clock = gpu.clock.mem_clock
    video_clock = gpu.clock.video_clock
    graphics_clock_max = gpu.clock.graphics_clock_max
    sm_clock_max = gpu.clock.sm_clock_max
    mem_clock_max = gpu.clock.mem_clock_max
    video_clock_max = gpu.clock.video_clock_max

    info_texts: dict[str, str | None] = {
        "graphics_clock": None,
        "sm_clock": None,
        "mem_clock": None,
        "video_clock": None,
    }

    if graphics_clock is not None and graphics_clock_max is not None:
        info_texts["graphics_clock"] = (
            f"Graphics clock: {graphics_clock} MHz / {graphics_clock_max} MHz"
        )
    if sm_clock is not None and sm_clock_max is not None:
        info_texts["sm_clock"] = f"SM clock: {sm_clock} MHz / {sm_clock_max} MHz"
    if mem_clock is not None and mem_clock_max is not None:
        info_texts["mem_clock"] = f"MEM clock: {mem_clock} MHz / {mem_clock_max} MHz"
    if video_clock is not None and video_clock_max is not None:
        info_texts["video_clock"] = f"Video clock: {video_clock} MHz / {video_clock_max} MHz"

    info_text: str = ", ".join([info for info in info_texts.values() if info is not None])

    yield Result(state=State.OK, summary=info_text)

    # Clock speeds by nvidia-smi are given in MHz, check_mk expects them in hz for render.frequency
    if graphics_clock is not None and graphics_clock_max is not None:
        yield from check_levels_v1(
            graphics_clock * MHz_to_Hz_factor,
            levels_upper=params.get("levels_graphics_upper"),
            levels_lower=params.get("levels_graphics_lower"),
            render_func=render.frequency,
            metric_name="graphics_clock",
            boundaries=(0.0, graphics_clock_max * MHz_to_Hz_factor),
            label="Graphics clock",
            notice_only=True,
        )
        yield Metric("graphics_clock_max", graphics_clock_max * MHz_to_Hz_factor)

    if sm_clock is not None and sm_clock_max is not None:
        yield from check_levels_v1(
            sm_clock * MHz_to_Hz_factor,
            levels_upper=params.get("levels_sm_upper"),
            levels_lower=params.get("levels_sm_lower"),
            render_func=render.frequency,
            metric_name="sm_clock",
            boundaries=(0.0, sm_clock_max * MHz_to_Hz_factor),
            label="SM clock",
            notice_only=True,
        )
        yield Metric("sm_clock_max", sm_clock_max * MHz_to_Hz_factor)

    if mem_clock is not None and mem_clock_max is not None:
        yield from check_levels_v1(
            mem_clock * MHz_to_Hz_factor,
            levels_upper=params.get("levels_mem_upper"),
            levels_lower=params.get("levels_mem_lower"),
            render_func=render.frequency,
            metric_name="mem_clock",
            boundaries=(0.0, mem_clock_max * MHz_to_Hz_factor),
            label="MEM clock",
            notice_only=True,
        )
        yield Metric("mem_clock_max", mem_clock_max * MHz_to_Hz_factor)

    if video_clock is not None and video_clock_max is not None:
        yield from check_levels_v1(
            video_clock * MHz_to_Hz_factor,
            levels_upper=params.get("levels_video_upper"),
            levels_lower=params.get("levels_video_lower"),
            render_func=render.frequency,
            metric_name="video_clock",
            boundaries=(0.0, video_clock_max * MHz_to_Hz_factor),
            label="Video clock",
            notice_only=True,
        )
        yield Metric("video_clock_max", video_clock_max * MHz_to_Hz_factor)


check_plugin_nvidia_smi_clock_speed = CheckPlugin(
    name="nvidia_smi_clock_speed",
    service_name="Nvidia GPU Clock speed %s",
    sections=["nvidia_smi"],
    discovery_function=discover_nvidia_smi_clock_speed,
    check_ruleset_name="nvidia_smi_clock_speed",
    check_default_parameters=ClockParams(
        levels_graphics_upper=None,
        levels_graphics_lower=None,
        levels_sm_upper=None,
        levels_sm_lower=None,
        levels_mem_upper=None,
        levels_mem_lower=None,
        levels_video_upper=None,
        levels_video_lower=None,
    ),
    check_function=check_nvidia_smi_clock_speed,
)
