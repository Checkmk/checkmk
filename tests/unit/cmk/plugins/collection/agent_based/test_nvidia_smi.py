#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import datetime

import pytest

from cmk.agent_based.v2 import (
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.collection.agent_based import nvidia_smi
from cmk.plugins.lib.temperature import TempParamType

STRING_TABLE = [
    ['<?xml version="1.0" ?>'],
    ['<!DOCTYPE nvidia_smi_log SYSTEM "nvsmi_device_v11.dtd">'],
    ["<nvidia_smi_log>"],
    ["<timestamp>Wed Aug 24 13:24:02 2022</timestamp>"],
    ["<driver_version>516.40</driver_version>"],
    ["<cuda_version>11.7</cuda_version>"],
    ["<attached_gpus>1</attached_gpus>"],
    ['<gpu id="00000000:0B:00.0">'],
    ["<product_name>NVIDIA GeForce RTX 2070 SUPER</product_name>"],
    ["<product_brand>GeForce</product_brand>"],
    ["<product_architecture>Turing</product_architecture>"],
    ["<display_mode>Enabled</display_mode>"],
    ["<display_active>Enabled</display_active>"],
    ["<persistence_mode>N/A</persistence_mode>"],
    ["<mig_mode>"],
    ["<current_mig>N/A</current_mig>"],
    ["<pending_mig>N/A</pending_mig>"],
    ["</mig_mode>"],
    ["<mig_devices>"],
    ["None"],
    ["</mig_devices>"],
    ["<accounting_mode>Disabled</accounting_mode>"],
    ["<accounting_mode_buffer_size>4000</accounting_mode_buffer_size>"],
    ["<driver_model>"],
    ["<current_dm>WDDM</current_dm>"],
    ["<pending_dm>WDDM</pending_dm>"],
    ["</driver_model>"],
    ["<serial>N/A</serial>"],
    ["<uuid>GPU-a09831af-4ab2-c847-2cf0-115cf3ec46f0</uuid>"],
    ["<minor_number>N/A</minor_number>"],
    ["<vbios_version>90.04.76.00.d4</vbios_version>"],
    ["<multigpu_board>No</multigpu_board>"],
    ["<board_id>0xb00</board_id>"],
    ["<gpu_part_number>N/A</gpu_part_number>"],
    ["<gpu_module_id>0</gpu_module_id>"],
    ["<inforom_version>"],
    ["<img_version>G001.0000.02.04</img_version>"],
    ["<oem_object>1.1</oem_object>"],
    ["<ecc_object>N/A</ecc_object>"],
    ["<pwr_object>N/A</pwr_object>"],
    ["</inforom_version>"],
    ["<gpu_operation_mode>"],
    ["<current_gom>N/A</current_gom>"],
    ["<pending_gom>N/A</pending_gom>"],
    ["</gpu_operation_mode>"],
    ["<gsp_firmware_version>N/A</gsp_firmware_version>"],
    ["<gpu_virtualization_mode>"],
    ["<virtualization_mode>None</virtualization_mode>"],
    ["<host_vgpu_mode>N/A</host_vgpu_mode>"],
    ["</gpu_virtualization_mode>"],
    ["<ibmnpu>"],
    ["<relaxed_ordering_mode>N/A</relaxed_ordering_mode>"],
    ["</ibmnpu>"],
    ["<pci>"],
    ["<pci_bus>0B</pci_bus>"],
    ["<pci_device>00</pci_device>"],
    ["<pci_domain>0000</pci_domain>"],
    ["<pci_device_id>1E8410DE</pci_device_id>"],
    ["<pci_bus_id>00000000:0B:00.0</pci_bus_id>"],
    ["<pci_sub_system_id>3FF61458</pci_sub_system_id>"],
    ["<pci_gpu_link_info>"],
    ["<pcie_gen>"],
    ["<max_link_gen>3</max_link_gen>"],
    ["<current_link_gen>3</current_link_gen>"],
    ["</pcie_gen>"],
    ["<link_widths>"],
    ["<max_link_width>16x</max_link_width>"],
    ["<current_link_width>16x</current_link_width>"],
    ["</link_widths>"],
    ["</pci_gpu_link_info>"],
    ["<pci_bridge_chip>"],
    ["<bridge_chip_type>N/A</bridge_chip_type>"],
    ["<bridge_chip_fw>N/A</bridge_chip_fw>"],
    ["</pci_bridge_chip>"],
    ["<replay_counter>0</replay_counter>"],
    ["<replay_rollover_counter>0</replay_rollover_counter>"],
    ["<tx_util>16000 KB/s</tx_util>"],
    ["<rx_util>18000 KB/s</rx_util>"],
    ["</pci>"],
    ["<fan_speed>0 %</fan_speed>"],
    ["<performance_state>P0</performance_state>"],
    ["<fb_memory_usage>"],
    ["<total>8192 MiB</total>"],
    ["<reserved>181 MiB</reserved>"],
    ["<used>1071 MiB</used>"],
    ["<free>6939 MiB</free>"],
    ["</fb_memory_usage>"],
    ["<bar1_memory_usage>"],
    ["<total>256 MiB</total>"],
    ["<used>2 MiB</used>"],
    ["<free>254 MiB</free>"],
    ["</bar1_memory_usage>"],
    ["<compute_mode>Default</compute_mode>"],
    ["<utilization>"],
    ["<gpu_util>5 %</gpu_util>"],
    ["<memory_util>10 %</memory_util>"],
    ["<encoder_util>3 %</encoder_util>"],
    ["<decoder_util>8 %</decoder_util>"],
    ["</utilization>"],
    ["<encoder_stats>"],
    ["<session_count>0</session_count>"],
    ["<average_fps>0</average_fps>"],
    ["<average_latency>0</average_latency>"],
    ["</encoder_stats>"],
    ["<fbc_stats>"],
    ["<session_count>0</session_count>"],
    ["<average_fps>0</average_fps>"],
    ["<average_latency>0</average_latency>"],
    ["</fbc_stats>"],
    ["<ecc_mode>"],
    ["<current_ecc>N/A</current_ecc>"],
    ["<pending_ecc>N/A</pending_ecc>"],
    ["</ecc_mode>"],
    ["<ecc_errors>"],
    ["<volatile>"],
    ["<sram_correctable>N/A</sram_correctable>"],
    ["<sram_uncorrectable>N/A</sram_uncorrectable>"],
    ["<dram_correctable>N/A</dram_correctable>"],
    ["<dram_uncorrectable>N/A</dram_uncorrectable>"],
    ["</volatile>"],
    ["<aggregate>"],
    ["<sram_correctable>N/A</sram_correctable>"],
    ["<sram_uncorrectable>N/A</sram_uncorrectable>"],
    ["<dram_correctable>N/A</dram_correctable>"],
    ["<dram_uncorrectable>N/A</dram_uncorrectable>"],
    ["</aggregate>"],
    ["</ecc_errors>"],
    ["<retired_pages>"],
    ["<multiple_single_bit_retirement>"],
    ["<retired_count>N/A</retired_count>"],
    ["<retired_pagelist>N/A</retired_pagelist>"],
    ["</multiple_single_bit_retirement>"],
    ["<double_bit_retirement>"],
    ["<retired_count>N/A</retired_count>"],
    ["<retired_pagelist>N/A</retired_pagelist>"],
    ["</double_bit_retirement>"],
    ["<pending_blacklist>N/A</pending_blacklist>"],
    ["<pending_retirement>N/A</pending_retirement>"],
    ["</retired_pages>"],
    ["<remapped_rows>N/A</remapped_rows>"],
    ["<temperature>"],
    ["<gpu_temp>40 C</gpu_temp>"],
    ["<gpu_temp_max_threshold>95 C</gpu_temp_max_threshold>"],
    ["<gpu_temp_slow_threshold>92 C</gpu_temp_slow_threshold>"],
    ["<gpu_temp_max_gpu_threshold>88 C</gpu_temp_max_gpu_threshold>"],
    ["<gpu_target_temperature>83 C</gpu_target_temperature>"],
    ["<memory_temp>N/A</memory_temp>"],
    ["<gpu_temp_max_mem_threshold>N/A</gpu_temp_max_mem_threshold>"],
    ["</temperature>"],
    ["<supported_gpu_target_temp>"],
    ["<gpu_target_temp_min>65 C</gpu_target_temp_min>"],
    ["<gpu_target_temp_max>88 C</gpu_target_temp_max>"],
    ["</supported_gpu_target_temp>"],
    ["<power_readings>"],
    ["<power_state>P0</power_state>"],
    ["<power_management>Supported</power_management>"],
    ["<power_draw>49.44 W</power_draw>"],
    ["<power_limit>255.00 W</power_limit>"],
    ["<default_power_limit>255.00 W</default_power_limit>"],
    ["<enforced_power_limit>255.00 W</enforced_power_limit>"],
    ["<min_power_limit>105.00 W</min_power_limit>"],
    ["<max_power_limit>314.00 W</max_power_limit>"],
    ["</power_readings>"],
    ["<clocks>"],
    ["<graphics_clock>1244 MHz</graphics_clock>"],
    ["<sm_clock>1244 MHz</sm_clock>"],
    ["<mem_clock>6993 MHz</mem_clock>"],
    ["<video_clock>1154 MHz</video_clock>"],
    ["</clocks>"],
    ["<applications_clocks>"],
    ["<graphics_clock>N/A</graphics_clock>"],
    ["<mem_clock>N/A</mem_clock>"],
    ["</applications_clocks>"],
    ["<default_applications_clocks>"],
    ["<graphics_clock>N/A</graphics_clock>"],
    ["<mem_clock>N/A</mem_clock>"],
    ["</default_applications_clocks>"],
    ["<max_clocks>"],
    ["<graphics_clock>2475 MHz</graphics_clock>"],
    ["<sm_clock>2475 MHz</sm_clock>"],
    ["<mem_clock>7001 MHz</mem_clock>"],
    ["<video_clock>1950 MHz</video_clock>"],
    ["</max_clocks>"],
    ["<max_customer_boost_clocks>"],
    ["<graphics_clock>N/A</graphics_clock>"],
    ["</max_customer_boost_clocks>"],
    ["<clock_policy>"],
    ["<auto_boost>N/A</auto_boost>"],
    ["<auto_boost_default>N/A</auto_boost_default>"],
    ["</clock_policy>"],
    ["<voltage>"],
    ["<graphics_volt>N/A</graphics_volt>"],
    ["</voltage>"],
    ["</gpu>"],
    ["</nvidia_smi_log>"],
]

SECTION = nvidia_smi.Section(
    timestamp=datetime.datetime(2022, 8, 24, 13, 24, 2),
    driver_version="516.40",
    cuda_version="11.7",
    attached_gpus=1,
    gpus={
        "00000000:0B:00.0": nvidia_smi.GPU(
            id="00000000:0B:00.0",
            product_name="NVIDIA GeForce RTX 2070 SUPER",
            product_brand="GeForce",
            power_readings=nvidia_smi.PowerReadings(
                power_state="P0",
                power_management=nvidia_smi.PowerManagement.SUPPORTED,
                power_draw=49.44,
                power_limit=255.0,
                default_power_limit=255.0,
                enforced_power_limit=255.0,
                min_power_limit=105.0,
                max_power_limit=314.0,
            ),
            temperature=nvidia_smi.Temperature(
                gpu_temp=40.0,
                gpu_temp_max_threshold=95.0,
                gpu_temp_slow_threshold=92.0,
                gpu_target_temperature=83.0,
                memory_temp=None,
                gpu_temp_max_mem_threshold=None,
            ),
            utilization=nvidia_smi.Utilization(
                memory_util=nvidia_smi.MemoryUtilization(
                    fb_memory_usage=nvidia_smi.MemoryUsage(
                        total=8589934592.0,
                        used=1123024896.0,
                        free=7276068864.0,
                    ),
                    bar1_memory_usage=nvidia_smi.MemoryUsage(
                        total=268435456.0,
                        used=2097152.0,
                        free=266338304.0,
                    ),
                ),
                gpu_util=5.0,
                encoder_util=3.0,
                decoder_util=8.0,
            ),
        )
    },
)


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        (
            STRING_TABLE,
            SECTION,
        ),
    ],
)
def test_parse_nvidia_smi(
    string_table: StringTable,
    expected_result: nvidia_smi.Section,
) -> None:
    assert nvidia_smi.parse_nvidia_smi(string_table) == expected_result


@pytest.mark.parametrize(
    "section, expected_result",
    [
        (
            SECTION,
            [Service(item="00000000:0B:00.0")],
        ),
    ],
)
def test_discover_nvidia_smi_temperature(
    section: nvidia_smi.Section,
    expected_result: DiscoveryResult,
) -> None:
    assert list(nvidia_smi.discover_nvidia_smi_temperature(section)) == expected_result


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize(
    "item, params, section, expected_result",
    [
        (
            "00000000:0B:00.0",
            {},
            SECTION,
            [
                Metric("temp", 40.0),
                Result(state=State.OK, summary="Temperature: 40.0 °C"),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (no levels found)",
                ),
            ],
        ),
    ],
)
def test_check_nvidia_smi_temperature(
    item: str,
    params: TempParamType,
    section: nvidia_smi.Section,
    expected_result: CheckResult,
) -> None:
    assert list(nvidia_smi.check_nvidia_smi_temperature(item, params, section)) == expected_result


@pytest.mark.parametrize(
    "section, expected_result",
    [
        (
            SECTION,
            [Service(item="00000000:0B:00.0")],
        ),
    ],
)
def test_discover_nvidia_smi_gpu_util(
    section: nvidia_smi.Section,
    expected_result: DiscoveryResult,
) -> None:
    assert list(nvidia_smi.discover_nvidia_smi_gpu_util(section)) == expected_result


@pytest.mark.parametrize(
    "item, params, section, expected_result",
    [
        (
            "00000000:0B:00.0",
            {},
            SECTION,
            [
                Result(state=State.OK, summary="Utilization: 5.00%"),
                Metric("gpu_utilization", 5.0),
            ],
        ),
        (
            "00000000:0B:00.0",
            nvidia_smi.GenericLevelsParam(levels=(2.0, 4.0)),
            SECTION,
            [
                Result(state=State.CRIT, summary="Utilization: 5.00% (warn/crit at 2.00%/4.00%)"),
                Metric("gpu_utilization", 5.0, levels=(2.0, 4.0)),
            ],
        ),
    ],
)
def test_check_nvidia_smi_gpu_util(
    item: str,
    params: nvidia_smi.GenericLevelsParam,
    section: nvidia_smi.Section,
    expected_result: CheckResult,
) -> None:
    assert list(nvidia_smi.check_nvidia_smi_gpu_util(item, params, section)) == expected_result


@pytest.mark.parametrize(
    "section, expected_result",
    [
        (
            SECTION,
            [Service(item="00000000:0B:00.0")],
        ),
    ],
)
def test_discover_nvidia_smi_en_de_coder_util(
    section: nvidia_smi.Section,
    expected_result: DiscoveryResult,
) -> None:
    assert list(nvidia_smi.discover_nvidia_smi_en_de_coder_util(section)) == expected_result


@pytest.mark.parametrize(
    "item, params, section, expected_result",
    [
        (
            "00000000:0B:00.0",
            {},
            SECTION,
            [
                Result(state=State.OK, summary="Encoder: 3.00%"),
                Metric("encoder_utilization", 3.0),
                Result(state=State.OK, summary="Decoder: 8.00%"),
                Metric("decoder_utilization", 8.0),
            ],
        ),
        (
            "00000000:0B:00.0",
            nvidia_smi.DeEnCoderParams(encoder_levels=(2.5, 3.5), decoder_levels=(5.0, 10.0)),
            SECTION,
            [
                Result(state=State.WARN, summary="Encoder: 3.00% (warn/crit at 2.50%/3.50%)"),
                Metric("encoder_utilization", 3.0, levels=(2.5, 3.5)),
                Result(state=State.WARN, summary="Decoder: 8.00% (warn/crit at 5.00%/10.00%)"),
                Metric("decoder_utilization", 8.0, levels=(5.0, 10.0)),
            ],
        ),
    ],
)
def test_check_nvidia_smi_en_de_coder_util(
    item: str,
    params: nvidia_smi.DeEnCoderParams,
    section: nvidia_smi.Section,
    expected_result: CheckResult,
) -> None:
    assert (
        list(nvidia_smi.check_nvidia_smi_en_de_coder_util(item, params, section)) == expected_result
    )


@pytest.mark.parametrize(
    "section, expected_result",
    [
        (
            SECTION,
            [Service(item="00000000:0B:00.0")],
        ),
    ],
)
def test_discover_nvidia_smi_power(
    section: nvidia_smi.Section,
    expected_result: DiscoveryResult,
) -> None:
    assert list(nvidia_smi.discover_nvidia_smi_power(section)) == expected_result


@pytest.mark.parametrize(
    "item, params, section, expected_result",
    [
        (
            "00000000:0B:00.0",
            {},
            SECTION,
            [
                Result(state=State.OK, summary="Power Draw: 49.44 W"),
                Metric("power_usage", 49.44, levels=(255.0, 255.0), boundaries=(0.0, 255.0)),
                Result(state=State.OK, notice="Power limit: 255.0 W"),
                Result(state=State.OK, notice="Min power limit: 105.0 W"),
                Result(state=State.OK, notice="Max power limit: 314.0 W"),
            ],
        ),
        (
            "00000000:0B:00.0",
            nvidia_smi.GenericLevelsParam(levels=(30.0, 40.0)),
            SECTION,
            [
                Result(
                    state=State.CRIT, summary="Power Draw: 49.44 W (warn/crit at 30.00 W/40.00 W)"
                ),
                Metric("power_usage", 49.44, levels=(30.0, 40.0), boundaries=(0.0, 255.0)),
                Result(state=State.OK, notice="Power limit: 255.0 W"),
                Result(state=State.OK, notice="Min power limit: 105.0 W"),
                Result(state=State.OK, notice="Max power limit: 314.0 W"),
            ],
        ),
    ],
)
def test_check_nvidia_smi_power(
    item: str,
    params: nvidia_smi.GenericLevelsParam,
    section: nvidia_smi.Section,
    expected_result: CheckResult,
) -> None:
    assert list(nvidia_smi.check_nvidia_smi_power(item, params, section)) == expected_result


@pytest.mark.parametrize(
    "section, expected_result",
    [
        (
            SECTION,
            [Service(item="00000000:0B:00.0")],
        ),
    ],
)
def test_discover_nvidia_smi_memory_util(
    section: nvidia_smi.Section,
    expected_result: DiscoveryResult,
) -> None:
    assert list(nvidia_smi.discover_nvidia_smi_memory_util(section)) == expected_result


@pytest.mark.parametrize(
    "item, params, section, expected_result",
    [
        (
            "00000000:0B:00.0",
            {},
            SECTION,
            [
                Result(state=State.OK, summary="Total memory: 12.70% - 1.05 GiB of 8.25 GiB"),
                Metric("mem_used_percent", 12.70123106060606, boundaries=(0.0, None)),
                Result(state=State.OK, summary="FB memory: 13.07% - 1.05 GiB of 8.00 GiB"),
                Metric("fb_mem_usage_used", 1123024896.0, boundaries=(0.0, 8589934592.0)),
                Metric("fb_mem_usage_free", 7276068864.0, boundaries=(0.0, 8589934592.0)),
                Metric("fb_mem_usage_total", 8589934592.0),
                Result(state=State.OK, summary="BAR1 memory: 0.78% - 2.00 MiB of 256 MiB"),
                Metric("bar1_mem_usage_used", 2097152.0, boundaries=(0.0, 268435456.0)),
                Metric("bar1_mem_usage_free", 266338304.0, boundaries=(0.0, 268435456.0)),
                Metric("bar1_mem_usage_total", 268435456.0),
            ],
        ),
        (
            "00000000:0B:00.0",
            nvidia_smi.MemoryParams(
                levels_total=(10.0, 20.0),
                levels_bar1=(0.5, 1.0),
                levels_fb=(5.0, 10.0),
            ),
            SECTION,
            [
                Result(
                    state=State.WARN,
                    summary="Total memory: 12.70% - 1.05 GiB of 8.25 GiB (warn/crit at 10.00%/20.00% used)",
                ),
                Metric(
                    "mem_used_percent",
                    12.70123106060606,
                    levels=(10.0, 20.0),
                    boundaries=(0.0, None),
                ),
                Result(
                    state=State.CRIT,
                    summary="FB memory: 13.07% - 1.05 GiB of 8.00 GiB (warn/crit at 5.00%/10.00% used)",
                ),
                Metric(
                    "fb_mem_usage_used",
                    1123024896.0,
                    levels=(429496729.6, 858993459.2),
                    boundaries=(0.0, 8589934592.0),
                ),
                Metric("fb_mem_usage_free", 7276068864.0, boundaries=(0.0, 8589934592.0)),
                Metric("fb_mem_usage_total", 8589934592.0),
                Result(
                    state=State.WARN,
                    summary="BAR1 memory: 0.78% - 2.00 MiB of 256 MiB (warn/crit at 0.50%/1.00% used)",
                ),
                Metric(
                    "bar1_mem_usage_used",
                    2097152.0,
                    levels=(1342177.28, 2684354.56),
                    boundaries=(0.0, 268435456.0),
                ),
                Metric("bar1_mem_usage_free", 266338304.0, boundaries=(0.0, 268435456.0)),
                Metric("bar1_mem_usage_total", 268435456.0),
            ],
        ),
    ],
)
def test_check_nvidia_smi_memory_util(
    item: str,
    params: nvidia_smi.MemoryParams,
    section: nvidia_smi.Section,
    expected_result: CheckResult,
) -> None:
    assert list(nvidia_smi.check_nvidia_smi_memory_util(item, params, section)) == expected_result
