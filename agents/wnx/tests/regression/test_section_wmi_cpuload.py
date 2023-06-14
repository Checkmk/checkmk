#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import re
from collections.abc import Sequence
from typing import Any, AnyStr, Final

import pytest

from . import it_utils
from .local import local_test


class Globals:
    section = "wmi_cpuload"
    alone = True


EXPECTED_SYSTEM_PERF_HEADER: Final[dict[str, str]] = {
    "use_wmi": (
        r"AlignmentFixupsPersec,Caption,ContextSwitchesPersec,Description,"
        r"ExceptionDispatchesPersec,FileControlBytesPersec,"
        r"FileControlOperationsPersec,FileDataOperationsPersec,"
        r"FileReadBytesPersec,FileReadOperationsPersec,FileWriteBytesPersec,"
        r"FileWriteOperationsPersec,FloatingEmulationsPersec,Frequency_Object,"
        r"Frequency_PerfTime,Frequency_Sys100NS,Name,"
        r"PercentRegistryQuotaInUse,PercentRegistryQuotaInUse_Base,Processes,"
        r"ProcessorQueueLength,SystemCallsPersec,SystemUpTime,Threads,"
        r"Timestamp_Object,Timestamp_PerfTime,Timestamp_Sys100NS,WMIStatus"
    ).replace(",", "\\|"),
    "use_perf": r"Name,ProcessorQueueLength,Timestamp_PerfTime,Frequency_PerfTime,WMIStatus".replace(
        ",", "\\|"
    ),
}

EXPECTED_SYSTEM_PERF_DATA: Final[dict[str, str]] = {
    "use_wmi": (
        r"\d+,,\d+,,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,,\d+,"
        r"\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\b(?:OK|Timeout)\b"
    ).replace(",", "\\|"),
    "use_perf": r",\d+,\d+,\d+,OK".replace(",", "\\|"),
}

EXPECTED_COMPUTER_SYSTEM_HEADER: Final[dict[str, str]] = {
    "use_wmi": (
        r"AdminPasswordStatus,AutomaticManagedPagefile,"
        r"AutomaticResetBootOption,AutomaticResetCapability,BootOptionOnLimit,"
        r"BootOptionOnWatchDog,BootROMSupported,BootStatus,BootupState,"
        r"Caption,ChassisBootupState,ChassisSKUNumber,CreationClassName,"
        r"CurrentTimeZone,DaylightInEffect,Description,DNSHostName,Domain,"
        r"DomainRole,EnableDaylightSavingsTime,FrontPanelResetStatus,"
        r"HypervisorPresent,InfraredSupported,InitialLoadInfo,InstallDate,"
        r"KeyboardPasswordStatus,LastLoadInfo,Manufacturer,Model,Name,"
        r"NameFormat,NetworkServerModeEnabled,NumberOfLogicalProcessors,"
        r"NumberOfProcessors,OEMLogoBitmap,OEMStringArray,PartOfDomain,"
        r"PauseAfterReset,PCSystemType,PCSystemTypeEx,"
        r"PowerManagementCapabilities,PowerManagementSupported,"
        r"PowerOnPasswordStatus,PowerState,PowerSupplyState,"
        r"PrimaryOwnerContact,PrimaryOwnerName,ResetCapability,ResetCount,"
        r"ResetLimit,Roles,Status,SupportContactDescription,SystemFamily,"
        r"SystemSKUNumber,SystemStartupDelay,SystemStartupOptions,"
        r"SystemStartupSetting,SystemType,ThermalState,TotalPhysicalMemory,"
        r"UserName,WakeUpType,Workgroup,WMIStatus"
    ).replace(",", "\\|"),
    "use_perf": r"Name,NumberOfLogicalProcessors,NumberOfProcessors,WMIStatus".replace(",", "\\|"),
}

EXPECTED_COMPUTER_SYSTEM_DATA: Final[dict[str, str]] = {
    "use_wmi": (
        r"\d+,\d+,\d+,\d+,\d*,\d*,\d+,[^,]*,[^,]+,[\w-]+,\d+,[^,]*,\w+,\d+,\d+,"
        r"[^,]+,[\w-]+,[^,]+,\d+,\d+,\d+,\d+,\d+,,,\d+,,[^,]+(, [^,]+)?,[^,]+,"
        r"[\w-]+,,\d+,\d+,\d+,,[^,]*,\d+,\-?\d+,\d+,\d+,,,\d+,\d+,\d+,,[^,]+,"
        r"\d+,\d+,\d+,[^,]+,\w+,,[^,]*,[^,]*,,,,[^,]+,\d+,\d+,[^,]*,\d+,\w*,\b(?:OK|Timeout)\b"
    ).replace(",", "\\|"),
    "use_perf": r"[^,]*,\d+,\d+,OK".replace(",", "\\|"),
}


@pytest.fixture(name="testfile")
def testfile_engine() -> str:
    return os.path.basename(__file__)


@pytest.fixture(name="config_with_cpuload_method", params=["use_wmi", "use_perf"])
def change_config_cpuload_method(  # type: ignore[no-untyped-def]
    request, make_yaml_config
) -> dict[str, Any]:
    make_yaml_config["global"]["cpuload_method"] = request.param
    return make_yaml_config


@pytest.fixture(name="testconfig", params=["alone", "with_systemtime"])
def fixture_testconfig(  # type: ignore[no-untyped-def]
    request, config_with_cpuload_method
) -> dict[str, Any]:
    Globals.alone = request.param == "alone"
    config_with_cpuload_method["global"]["sections"] = (
        Globals.section if Globals.alone else [Globals.section, "systemtime"]
    )
    config_with_cpuload_method["global"]["wmi_timeout"] = 10
    return config_with_cpuload_method


@pytest.fixture(name="expected")
def expected_output_engine(testconfig) -> Sequence[str]:  # type: ignore[no-untyped-def]
    method = testconfig["global"]["cpuload_method"]
    expected = [
        re.escape(f"<<<{Globals.section}:sep(124)>>>"),
        re.escape("[system_perf]"),
        EXPECTED_SYSTEM_PERF_HEADER[method],
        EXPECTED_SYSTEM_PERF_DATA[method],
        re.escape("[computer_system]"),
        EXPECTED_COMPUTER_SYSTEM_HEADER[method],
        EXPECTED_COMPUTER_SYSTEM_DATA[method],
    ]
    if not Globals.alone:
        expected += [re.escape(r"<<<systemtime>>>"), r"\d+"]
    return expected


def test_section_wmi_cpuload(  # type: ignore[no-untyped-def]
    expected: Sequence[str], actual_output: Sequence[str], testfile: AnyStr
):
    required_lines = 7
    name = "cpu_load"

    if not it_utils.check_actual_input(name, required_lines, Globals.alone, actual_output):
        return

    local_test(expected, actual_output, testfile)
