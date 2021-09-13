#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import re

import pytest  # type: ignore[import]

from . import it_utils
from .local import local_test


class Globals(object):
    section = "wmi_cpuload"
    alone = True


@pytest.fixture(name="testfile")
def testfile_engine():
    return os.path.basename(__file__)


@pytest.fixture(params=["alone", "with_systemtime"])
def testconfig(request, make_yaml_config):
    Globals.alone = request.param == "alone"
    if Globals.alone:
        make_yaml_config["global"]["sections"] = Globals.section
    else:
        make_yaml_config["global"]["sections"] = [Globals.section, "systemtime"]
    return make_yaml_config


@pytest.fixture(name="expected_output")
def expected_output_engine():
    expected = [
        re.escape(r"<<<%s:sep(124)>>>" % Globals.section),
        re.escape(r"[system_perf]"),
        (
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
        (
            r"\d+,,\d+,,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,,\d+,"
            r"\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\b(?:OK|Timeout)\b"
        ).replace(",", "\\|"),
        re.escape(r"[computer_system]"),
        (
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
        (
            r"\d+,\d+,\d+,\d+,\d*,\d*,\d+,[^,]*,[^,]+,[\w-]+,\d+,[^,]*,\w+,\d+,\d+,"
            r"[^,]+,[\w-]+,[^,]+,\d+,\d+,\d+,\d+,\d+,,,\d+,,[^,]+(, [^,]+)?,[^,]+,"
            r"[\w-]+,,\d+,\d+,\d+,,[^,]*,\d+,\-?\d+,\d+,\d+,,,\d+,\d+,\d+,,[^,]+,"
            r"\d+,\d+,\d+,[^,]+,\w+,,[^,]*,[^,]*,,,,[^,]+,\d+,\d+,[^,]*,\d+,\w*,\b(?:OK|Timeout)\b"
        ).replace(",", "\\|"),
    ]
    if not Globals.alone:
        expected += [re.escape(r"<<<systemtime>>>"), r"\d+"]
    return expected


def test_section_wmi_cpuload(request, testconfig, expected_output, actual_output, testfile):
    # special case, wmi may timeout
    required_lines = 7
    name = "cpu_load"

    if not it_utils.check_actual_input(name, required_lines, Globals.alone, actual_output):
        return

    local_test(expected_output, actual_output, testfile, request.node.name)
