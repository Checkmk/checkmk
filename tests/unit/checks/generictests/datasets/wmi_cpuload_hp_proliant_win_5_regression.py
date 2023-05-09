#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'wmi_cpuload'

info = [
    [u'[system_perf]'],
    [
        u'AlignmentFixupsPersec', u'Caption', u'ContextSwitchesPersec', u'Description',
        u'ExceptionDispatchesPersec', u'FileControlBytesPersec', u'FileControlOperationsPersec',
        u'FileDataOperationsPersec', u'FileReadBytesPersec', u'FileReadOperationsPersec',
        u'FileWriteBytesPersec', u'FileWriteOperationsPersec', u'FloatingEmulationsPersec',
        u'Frequency_Object', u'Frequency_PerfTime', u'Frequency_Sys100NS', u'Name',
        u'PercentRegistryQuotaInUse', u'PercentRegistryQuotaInUse_Base', u'Processes',
        u'ProcessorQueueLength', u'SystemCallsPersec', u'SystemUpTime', u'Threads',
        u'Timestamp_Object', u'Timestamp_PerfTime', u'Timestamp_Sys100NS'
    ],
    [
        u'0', u'', u'-69479562', u'', u'14178685', u'804099358366', u'-783070306', u'1533491993',
        u'154737860718293', u'422989950', u'3094169943814', u'1110502043', u'0', u'10000000',
        u'2734511', u'10000000', u'', u'152069756', u'2147483647', u'132', u'0', u'-655373265',
        u'131051948225967966', u'2964', u'131096941722079880', u'12303331974804',
        u'131097013722070000'
    ], [u'[computer_system]'],
    [
        u'AdminPasswordStatus', u'AutomaticManagedPagefile', u'AutomaticResetBootOption',
        u'AutomaticResetCapability', u'BootOptionOnLimit', u'BootOptionOnWatchDog',
        u'BootROMSupported', u'BootupState', u'Caption', u'ChassisBootupState',
        u'CreationClassName', u'CurrentTimeZone', u'DaylightInEffect', u'Description',
        u'DNSHostName', u'Domain', u'DomainRole', u'EnableDaylightSavingsTime',
        u'FrontPanelResetStatus', u'InfraredSupported', u'InitialLoadInfo', u'InstallDate',
        u'KeyboardPasswordStatus', u'LastLoadInfo', u'Manufacturer', u'Model', u'Name',
        u'NameFormat', u'NetworkServerModeEnabled', u'NumberOfLogicalProcessors',
        u'NumberOfProcessors', u'OEMLogoBitmap', u'OEMStringArray', u'PartOfDomain',
        u'PauseAfterReset', u'PCSystemType', u'PowerManagementCapabilities',
        u'PowerManagementSupported', u'PowerOnPasswordStatus', u'PowerState', u'PowerSupplyState',
        u'PrimaryOwnerContact', u'PrimaryOwnerName', u'ResetCapability', u'ResetCount',
        u'ResetLimit', u'Roles', u'Status', u'SupportContactDescription', u'SystemStartupDelay',
        u'SystemStartupOptions', u'SystemStartupSetting', u'SystemType', u'ThermalState',
        u'TotalPhysicalMemory', u'UserName', u'WakeUpType', u'Workgroup'
    ],
    [
        u'3', u'0', u'1', u'1', u'', u'', u'1', u'Normal boot', u'ROZRHPDB09', u'3',
        u'Win32_ComputerSystem', u'120', u'1', u'AT/AT COMPATIBLE', u'ROZRHPDB09',
        u'testch.testint.net', u'3', u'1', u'3', u'0', u'', u'', u'3', u'', u'HP',
        u'ProLiant DL380 G6', u'ROZRHPDB09', u'', u'1', u'16', u'2', u'', u'<array>', u'1', u'-1',
        u'0', u'', u'', u'3', u'0', u'3', u'', u'test International', u'1', u'-1', u'-1',
        u'<array>', u'OK', u'', u'', u'', u'', u'x64-based PC', u'3', u'77298651136', u'', u'6', u''
    ]
]

discovery = {'': [(None, None)]}

checks = {
    '': [(
        None,
        {},
        [(
            0,
            "15 min load: 0.00 at 16 logical cores (0.00 per core)",
            [('load1', 0, None, None, 0, 16), ('load5', 0, None, None, 0, 16),
             ('load15', 0, None, None, 0, 16)],
        )],
    ),],
}
