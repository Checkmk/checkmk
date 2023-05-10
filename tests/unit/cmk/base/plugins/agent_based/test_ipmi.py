#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    Metric,
    Result,
    Service,
    State,
)
from cmk.base.plugins.agent_based import ipmi

from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult, DiscoveryResult
from cmk.base.plugins.agent_based.utils import ipmi as ipmi_utils

SECTION_IPMI = ipmi.parse_ipmi(
    [[
        u'Ambient', u'18.500', u'degrees_C', u'ok', u'na', u'1.000', u'6.000', u'37.000', u'42.000',
        u'na'
    ],
     [
         u'Systemboard', u'28.000', u'degrees_C', u'ok', u'na', u'na', u'na', u'75.000', u'80.000',
         u'na'
     ], [u'CPU', u'33.000', u'degrees_C', u'ok', u'na', u'na', u'na', u'95.000', u'99.000', u'na'],
     [u'MEM_A', u'21.000', u'degrees_C', u'ok', u'na', u'na', u'na', u'78.000', u'82.000', u'na'],
     [u'MEM_B', u'21.000', u'degrees_C', u'ok', u'na', u'na', u'na', u'78.000', u'82.000', u'na'],
     [
         u'PSU1_Inlet', u'29.000', u'degrees_C', u'ok', u'na', u'na', u'na', u'57.000', u'61.000',
         u'na'
     ],
     [
         u'PSU2_Inlet', u'28.000', u'degrees_C', u'ok', u'na', u'na', u'na', u'57.000', u'61.000',
         u'na'
     ],
     [u'PSU1', u'56.000', u'degrees_C', u'ok', u'na', u'na', u'na', u'102.000', u'107.000', u'na'],
     [u'PSU2', u'58.000', u'degrees_C', u'ok', u'na', u'na', u'na', u'102.000', u'107.000', u'na'],
     [u'BATT_3.0V', u'3.270', u'Volts', u'ok', u'na', u'2.025', u'2.295', u'na', u'3.495', u'na'],
     [u'STBY_3.3V', u'3.350', u'Volts', u'ok', u'na', u'3.033', u'na', u'na', u'3.567', u'na'],
     [u'iRMC_1.8V_STBY', u'1.790', u'Volts', u'ok', u'na', u'1.670', u'na', u'na', u'1.930', u'na'],
     [u'iRMC_1.5V_STBY', u'1.500', u'Volts', u'ok', u'na', u'1.390', u'na', u'na', u'1.610', u'na'],
     [u'iRMC_1.0V_STBY', u'0.980', u'Volts', u'ok', u'na', u'0.930', u'na', u'na', u'1.080', u'na'],
     [u'MAIN_12V', u'12.540', u'Volts', u'ok', u'na', u'11.100', u'na', u'na', u'12.960', u'na'],
     [u'MAIN_5V', u'5.212', u'Volts', u'ok', u'na', u'4.624', u'na', u'na', u'5.400', u'na'],
     [u'MAIN_3.3V', u'3.333', u'Volts', u'ok', u'na', u'3.033', u'na', u'na', u'3.567', u'na'],
     [u'MEM_1.35V', u'1.360', u'Volts', u'ok', u'na', u'1.250', u'na', u'na', u'1.610', u'na'],
     [u'PCH_1.05V', u'1.040', u'Volts', u'ok', u'na', u'0.970', u'na', u'na', u'1.130', u'na'],
     [u'MEM_VTT_0.68V', u'0.660', u'Volts', u'ok', u'na', u'0.630', u'na', u'na', u'0.810', u'na'],
     [u'FAN1_SYS', u'5160.000', u'RPM', u'ok', u'na', u'600.000', u'na', u'na', u'na', u'na'],
     [u'FAN2_SYS', u'2400.000', u'RPM', u'ok', u'na', u'600.000', u'na', u'na', u'na', u'na'],
     [u'FAN3_SYS', u'2400.000', u'RPM', u'ok', u'na', u'600.000', u'na', u'na', u'na', u'na'],
     [u'FAN4_SYS', u'1980.000', u'RPM', u'ok', u'na', u'600.000', u'na', u'na', u'na', u'na'],
     [u'FAN5_SYS', u'2280.000', u'RPM', u'nc', u'na', u'600.000', u'na', u'na', u'na', u'na'],
     [u'FAN_PSU1', u'2320.000', u'RPM', u'ok', u'na', u'400.000', u'na', u'na', u'na', u'na'],
     [u'FAN_PSU2', u'2400.000', u'RPM', u'ok', u'na', u'400.000', u'na', u'na', u'na', u'na'],
     [u'PSU1_Power', u'18.000', u'Watts', u'ok', u'na', u'na', u'na', u'na', u'na', u'na'],
     [u'PSU2_Power', u'30.000', u'Watts', u'ok', u'na', u'na', u'na', u'na', u'na', u'na'],
     [u'Total_Power', u'48.000', u'Watts', u'ok', u'na', u'na', u'na', u'na', u'498.000', u'na'],
     [u'Total_Power_Out', u'33.000', u'Watts', u'ok', u'na', u'na', u'na', u'na', u'na', u'na'],
     [
         u'I2C1_error_ratio', u'0.000', u'percent', u'ok', u'na', u'na', u'na', u'10.000',
         u'20.000', u'na'
     ],
     [
         u'I2C2_error_ratio', u'0.000', u'percent', u'ok', u'na', u'na', u'na', u'10.000',
         u'20.000', u'na'
     ],
     [
         u'I2C3_error_ratio', u'0.000', u'percent', u'ok', u'na', u'na', u'na', u'10.000',
         u'20.000', u'na'
     ],
     [
         u'I2C4_error_ratio', u'0.000', u'percent', u'ok', u'na', u'na', u'na', u'10.000',
         u'20.000', u'na'
     ],
     [
         u'I2C5_error_ratio', u'0.000', u'percent', u'ok', u'na', u'na', u'na', u'10.000',
         u'20.000', u'na'
     ],
     [
         u'I2C6_error_ratio', u'0.000', u'percent', u'ok', u'na', u'na', u'na', u'10.000',
         u'20.000', u'na'
     ],
     [
         u'I2C7_error_ratio', u'0.000', u'percent', u'ok', u'na', u'na', u'na', u'10.000',
         u'20.000', u'na'
     ],
     [
         u'I2C8_error_ratio', u'0.000', u'percent', u'ok', u'na', u'na', u'na', u'10.000',
         u'20.000', u'na'
     ], [u'SEL_Level', u'0.000', u'percent', u'ok', u'na', u'na', u'na', u'90.000', u'na', u'na']])

SECTION_IPMI_DISCRETE = ipmi.parse_ipmi(
    [[u'CMOS Battery     ', u' 10h ', u' ok  ', u'  7.1 ', u''],
     [u'ROMB Battery     ', u' 11h ', u' ok  ', u' 26.3 ', u''],
     [u'VCORE            ', u' 12h ', u' ok  ', u'  3.1 ', u' State Deasserted'],
     [u'VCORE            ', u' 13h ', u' ok  ', u'  3.2 ', u' State Deasserted'],
     [u'VCORE            ', u' 14h ', u' ok  ', u'  3.3 ', u' State Deasserted'],
     [u'VCORE            ', u' 15h ', u' ok  ', u'  3.4 ', u' State Deasserted'],
     [u'1.2V VDDR        ', u' 16h ', u' ok  ', u'  3.1 ', u' State Deasserted'],
     [u'1.2V VDDR        ', u' 17h ', u' ok  ', u'  3.2 ', u' State Deasserted'],
     [u'1.2V VDDR        ', u' 18h ', u' ok  ', u'  3.3 ', u' State Deasserted'],
     [u'1.2V VDDR        ', u' 19h ', u' ok  ', u'  3.4 ', u' State Deasserted'],
     [u'VR 1.8V AUX PG   ', u' 1Ah ', u' ok  ', u'  7.4 ', u' State Deasserted'],
     [u'VR 1.2V AUX PG   ', u' 1Bh ', u' ok  ', u'  7.4 ', u' State Deasserted'],
     [u'1.2V LOM PG      ', u' 1Ch ', u' ok  ', u'  7.4 ', u' State Deasserted'],
     [u'8V PG            ', u' 1Dh ', u' ok  ', u'  7.1 ', u' State Deasserted'],
     [u'1.2V AUX LOM PG  ', u' 1Eh ', u' ok  ', u'  7.1 ', u' State Deasserted'],
     [u'5V IO PG         ', u' 1Fh ', u' ok  ', u'  7.1 ', u' State Deasserted'],
     [u'5V CPU PG        ', u' 20h ', u' ok  ', u'  7.1 ', u' State Deasserted'],
     [u'3.3V PG          ', u' 21h ', u' ok  ', u'  7.1 ', u' State Deasserted'],
     [u'1.8V PG          ', u' 22h ', u' ok  ', u'  7.1 ', u' State Deasserted'],
     [u'1.1V PG          ', u' 24h ', u' ok  ', u'  7.1 ', u' State Deasserted'],
     [u'Mem1 0.75V PG    ', u' 26h ', u' ok  ', u'  8.1 ', u' State Deasserted'],
     [u'Mem2 0.75V PG    ', u' 27h ', u' ok  ', u'  8.2 ', u' State Deasserted'],
     [u'Mem3 0.75V PG    ', u' 28h ', u' ok  ', u'  8.3 ', u' State Deasserted'],
     [u'Mem4 0.75V PG    ', u' 29h ', u' ok  ', u'  8.4 ', u' State Deasserted'],
     [u'Mem5 0.75V PG    ', u' 2Ah ', u' ok  ', u'  8.5 ', u' State Deasserted'],
     [u'Mem6 0.75V PG    ', u' 2Bh ', u' ok  ', u'  8.6 ', u' State Deasserted'],
     [u'Mem7 0.75V PG    ', u' 2Ch ', u' ok  ', u'  8.7 ', u' State Deasserted'],
     [u'Mem8 0.75V PG    ', u' 2Dh ', u' ok  ', u'  8.8 ', u' State Deasserted'],
     [u'VR PLX PG        ', u' 2Eh ', u' ok  ', u'  7.8 ', u' State Deasserted'],
     [u'VR 1.2V NBSB PG  ', u' 2Fh ', u' ok  ', u'  7.8 ', u' State Deasserted'],
     [u'VR 2.5V CPU1     ', u' C0h ', u' ok  ', u'  9.8 ', u' State Deasserted'],
     [u'VR 2.5V CPU2     ', u' C1h ', u' ok  ', u'  9.8 ', u' State Deasserted'],
     [u'VR 2.5V CPU3     ', u' C2h ', u' ok  ', u'  9.8 ', u' State Deasserted'],
     [u'VR 2.5V CPU4     ', u' C3h ', u' ok  ', u'  9.8 ', u' State Deasserted'],
     [u'VR 1.2V CPU1     ', u' C4h ', u' ok  ', u'  9.8 ', u' State Deasserted'],
     [u'VR 1.2V CPU2     ', u' C5h ', u' ok  ', u'  9.8 ', u' State Deasserted'],
     [u'VR 1.2V CPU3     ', u' C6h ', u' ok  ', u'  9.8 ', u' State Deasserted'],
     [u'VR 1.2V CPU4     ', u' C7h ', u' ok  ', u'  9.8 ', u' State Deasserted'],
     [u'VR 1.5V MEM1     ', u' C8h ', u' ok  ', u'  8.8 ', u' State Deasserted'],
     [u'VR 1.5V MEM2     ', u' C9h ', u' ok  ', u'  8.8 ', u' State Deasserted'],
     [u'VR 1.5V MEM3     ', u' CAh ', u' ok  ', u'  8.8 ', u' State Deasserted'],
     [u'VR 1.5V MEM4     ', u' CBh ', u' ok  ', u'  8.8 ', u' State Deasserted'],
     [u'VR PSI MEM1      ', u' CCh ', u' ok  ', u'  8.8 ', u' State Deasserted'],
     [u'VR PSI MEM2      ', u' CDh ', u' ok  ', u'  8.8 ', u' State Deasserted'],
     [u'VR PSI MEM3      ', u' CEh ', u' ok  ', u'  8.8 ', u' State Deasserted'],
     [u'VR PSI MEM4      ', u' CFh ', u' ok  ', u'  8.8 ', u' State Deasserted'],
     [u'NB THERMTRIP     ', u' A1h ', u' ns  ', u'  7.1 ', u' Disabled'],
     [u'PFault Fail Safe ', u' 5Fh ', u' ns  ', u'  7.1 ', u' No Reading'],
     [u'Heatsink Pres    ', u' 5Dh ', u' ok  ', u'  7.1 ', u' Present'],
     [u'iDRAC6 Ent Pres  ', u' 70h ', u' ok  ', u'  7.1 ', u' Present'],
     [u'USB Cable Pres   ', u' 59h ', u' ok  ', u'  7.1 ', u' Present'],
     [u'Stor Adapt Pres  ', u' 5Ah ', u' ok  ', u'  7.1 ', u' Present'],
     [u'C Riser Pres     ', u' 5Bh ', u' ok  ', u'  7.1 ', u' Present'],
     [u'L Riser Pres     ', u' 5Ch ', u' ok  ', u'  7.1 ', u' Present'],
     [u'Presence         ', u' 50h ', u' ok  ', u'  3.1 ', u' Present'],
     [u'Presence         ', u' 51h ', u' ok  ', u'  3.2 ', u' Present'],
     [u'Presence         ', u' 52h ', u' ok  ', u'  3.3 ', u' Present'],
     [u'Presence         ', u' 53h ', u' ok  ', u'  3.4 ', u' Present'],
     [u'Presence         ', u' 54h ', u' ok  ', u' 10.1 ', u' Present'],
     [u'Presence         ', u' 55h ', u' ok  ', u' 10.2 ', u' Present'],
     [u'Presence         ', u' 58h ', u' ok  ', u' 26.1 ', u' Present'],
     [u'Status           ', u' 60h ', u' ok  ', u'  3.1 ', u' Presence detected'],
     [u'Status           ', u' 61h ', u' ok  ', u'  3.2 ', u' Presence detected'],
     [u'Status           ', u' 62h ', u' ok  ', u'  3.3 ', u' Presence detected'],
     [u'Status           ', u' 63h ', u' ok  ', u'  3.4 ', u' Presence detected'],
     [u'Status           ', u' 64h ', u' ok  ', u' 10.1 ', u' Presence detected'],
     [u'Status           ', u' 65h ', u' ok  ', u' 10.2 ', u' Presence detected'],
     [u'Riser Config     ', u' 68h ', u' ok  ', u'  7.1 ', u' Connected'],
     [u'OS Watchdog      ', u' 71h ', u' ok  ', u'  7.1 ', u''],
     [u'SEL              ', u' 72h ', u' ns  ', u'  7.1 ', u' No Reading'],
     [u'Intrusion        ', u' 73h ', u' ok  ', u'  7.1 ', u''],
     [u'PS Redundancy    ', u' 74h ', u' ok  ', u'  7.1 ', u' Fully Redundant'],
     [u'Fan Redundancy   ', u' 75h ', u' ok  ', u'  7.1 ', u' Fully Redundant'],
     [u'Power Optimized  ', u' 99h ', u' ok  ', u'  7.1 ', u' OEM Specific'],
     [u'Drive            ', u' 80h ', u' ok  ', u' 26.1 ', u' Drive Present'],
     [u'Cable SAS A      ', u' 90h ', u' ok  ', u' 26.1 ', u' Connected'],
     [u'Cable SAS B      ', u' 91h ', u' ok  ', u' 26.1 ', u' Connected'],
     [u'DKM Status       ', u' A0h ', u' ok  ', u'  7.1 ', u''],
     [u'SD1 Status       ', u' D0h ', u' ns  ', u' 11.1 ', u' Disabled'],
     [u'SD2 Status       ', u' D1h ', u' ns  ', u' 11.1 ', u' Disabled'],
     [u'SD Redundancy    ', u' D2h ', u' ns  ', u' 11.1 ', u' Disabled'],
     [u'VFlash           ', u' D3h ', u' ok  ', u' 11.2 ', u''],
     [u'ECC Corr Err     ', u' 01h ', u' ns  ', u' 34.1 ', u' No Reading'],
     [u'ECC Uncorr Err   ', u' 02h ', u' ns  ', u' 34.1 ', u' No Reading'],
     [u'I/O Channel Chk  ', u' 03h ', u' ns  ', u' 34.1 ', u' No Reading'],
     [u'PCI Parity Err   ', u' 04h ', u' ns  ', u' 34.1 ', u' No Reading'],
     [u'PCI System Err   ', u' 05h ', u' ns  ', u' 34.1 ', u' No Reading'],
     [u'SBE Log Disabled ', u' 06h ', u' ns  ', u' 34.1 ', u' No Reading'],
     [u'Logging Disabled ', u' 07h ', u' ns  ', u' 34.1 ', u' No Reading'],
     [u'Unknown          ', u' 08h ', u' ns  ', u' 34.1 ', u' No Reading'],
     [u'CPU Protocol Err ', u' 0Ah ', u' ns  ', u' 34.1 ', u' No Reading'],
     [u'CPU Bus PERR     ', u' 0Bh ', u' ns  ', u' 34.1 ', u' No Reading'],
     [u'CPU Init Err     ', u' 0Ch ', u' ns  ', u' 34.1 ', u' No Reading'],
     [u'CPU Machine Chk  ', u' 0Dh ', u' ns  ', u' 34.1 ', u' No Reading'],
     [u'Memory Spared    ', u' 11h ', u' ns  ', u' 34.1 ', u' No Reading'],
     [u'Memory Mirrored  ', u' 12h ', u' ns  ', u' 34.1 ', u' No Reading'],
     [u'Memory RAID      ', u' 13h ', u' ns  ', u' 34.1 ', u' No Reading'],
     [u'Memory Added     ', u' 14h ', u' ns  ', u' 34.1 ', u' No Reading'],
     [u'Memory Removed   ', u' 15h ', u' ns  ', u' 34.1 ', u' No Reading'],
     [u'Memory Cfg Err   ', u' 16h ', u' ns  ', u' 34.1 ', u' No Reading'],
     [u'Mem Redun Gain   ', u' 17h ', u' ns  ', u' 34.1 ', u' No Reading'],
     [u'PCIE Fatal Err   ', u' 18h ', u' ns  ', u' 34.1 ', u' No Reading'],
     [u'Chipset Err      ', u' 19h ', u' ns  ', u' 34.1 ', u' No Reading'],
     [u'Err Reg Pointer  ', u' 1Ah ', u' ns  ', u' 34.1 ', u' No Reading'],
     [u'Mem ECC Warning  ', u' 1Bh ', u' ns  ', u' 34.1 ', u' No Reading'],
     [u'Mem CRC Err      ', u' 1Ch ', u' ns  ', u' 34.1 ', u' No Reading'],
     [u'USB Over-current ', u' 1Dh ', u' ns  ', u' 34.1 ', u' No Reading'],
     [u'POST Err         ', u' 1Eh ', u' ns  ', u' 34.1 ', u' No Reading'],
     [u'Hdwr version err ', u' 1Fh ', u' ns  ', u' 34.1 ', u' No Reading'],
     [u'Mem Overtemp     ', u' 20h ', u' ns  ', u' 34.1 ', u' No Reading'],
     [u'Mem Fatal SB CRC ', u' 21h ', u' ns  ', u' 34.1 ', u' No Reading'],
     [u'Mem Fatal NB CRC ', u' 22h ', u' ns  ', u' 34.1 ', u' No Reading'],
     [u'OS Watchdog Time ', u' 23h ', u' ns  ', u' 34.1 ', u' No Reading'],
     [u'Non Fatal PCI Er ', u' 26h ', u' ns  ', u' 34.1 ', u' No Reading'],
     [u'Fatal IO Error   ', u' 27h ', u' ns  ', u' 34.1 ', u' No Reading'],
     [u'MSR Info Log     ', u' 28h ', u' ns  ', u' 34.1 ', u' No Reading'],
     [u'PS3 Status       ', u' C8h ', u' ok ', u' 10.1 ', u' Presence detected'],
     [u'PS4 Status       ', u' C9h ', u' ok ', u' 10.2 ', u' Presence detected'],
     [u'Pwr Unit Stat    ', u' 01h ', u' ok ', u' 21.1 ', u''],
     [u'Power Redundancy ', u' 02h ', u' ok ', u' 21.1 ', u' Fully Redundant'],
     [u'BMC Watchdog     ', u' 03h ', u' ok ', u'  7.1 ', u''],
     [u'PS1 Status       ', u' C8h ', u' ok ', u' 10.1 ', u' Presence detected, Failure detected'],
     [u'PS2 Status       ', u' C9h ', u' ok ', u' 10.2 ', u' Presence detected'],
     ["Drive 4          ", " 64h ", " ok  ", "  4.4 ", " Drive Present, Drive Fault"]])


@pytest.mark.parametrize('discovery_params, discovery_results', [
    (
        {
            "discovery_mode": ("summarize", {})
        },
        [Service(item='Summary', parameters={}, labels=[])],
    ),
    (
        {
            "discovery_mode": (
                "single",
                {
                    "ignored_sensors": ["VR_1.2V_CPU2", "Riser_Config"]
                },
            ),
        },
        [
            Service(item='CMOS_Battery', parameters={}, labels=[]),
            Service(item='ROMB_Battery', parameters={}, labels=[]),
            Service(item='VCORE', parameters={}, labels=[]),
            Service(item='1.2V_VDDR', parameters={}, labels=[]),
            Service(item='VR_1.8V_AUX_PG', parameters={}, labels=[]),
            Service(item='VR_1.2V_AUX_PG', parameters={}, labels=[]),
            Service(item='1.2V_LOM_PG', parameters={}, labels=[]),
            Service(item='8V_PG', parameters={}, labels=[]),
            Service(item='1.2V_AUX_LOM_PG', parameters={}, labels=[]),
            Service(item='5V_IO_PG', parameters={}, labels=[]),
            Service(item='5V_CPU_PG', parameters={}, labels=[]),
            Service(item='3.3V_PG', parameters={}, labels=[]),
            Service(item='1.8V_PG', parameters={}, labels=[]),
            Service(item='1.1V_PG', parameters={}, labels=[]),
            Service(item='Mem1_0.75V_PG', parameters={}, labels=[]),
            Service(item='Mem2_0.75V_PG', parameters={}, labels=[]),
            Service(item='Mem3_0.75V_PG', parameters={}, labels=[]),
            Service(item='Mem4_0.75V_PG', parameters={}, labels=[]),
            Service(item='Mem5_0.75V_PG', parameters={}, labels=[]),
            Service(item='Mem6_0.75V_PG', parameters={}, labels=[]),
            Service(item='Mem7_0.75V_PG', parameters={}, labels=[]),
            Service(item='Mem8_0.75V_PG', parameters={}, labels=[]),
            Service(item='VR_PLX_PG', parameters={}, labels=[]),
            Service(item='VR_1.2V_NBSB_PG', parameters={}, labels=[]),
            Service(item='VR_2.5V_CPU1', parameters={}, labels=[]),
            Service(item='VR_2.5V_CPU2', parameters={}, labels=[]),
            Service(item='VR_2.5V_CPU3', parameters={}, labels=[]),
            Service(item='VR_2.5V_CPU4', parameters={}, labels=[]),
            Service(item='VR_1.2V_CPU1', parameters={}, labels=[]),
            Service(item='VR_1.2V_CPU3', parameters={}, labels=[]),
            Service(item='VR_1.2V_CPU4', parameters={}, labels=[]),
            Service(item='VR_1.5V_MEM1', parameters={}, labels=[]),
            Service(item='VR_1.5V_MEM2', parameters={}, labels=[]),
            Service(item='VR_1.5V_MEM3', parameters={}, labels=[]),
            Service(item='VR_1.5V_MEM4', parameters={}, labels=[]),
            Service(item='VR_PSI_MEM1', parameters={}, labels=[]),
            Service(item='VR_PSI_MEM2', parameters={}, labels=[]),
            Service(item='VR_PSI_MEM3', parameters={}, labels=[]),
            Service(item='VR_PSI_MEM4', parameters={}, labels=[]),
            Service(item='Heatsink_Pres', parameters={}, labels=[]),
            Service(item='iDRAC6_Ent_Pres', parameters={}, labels=[]),
            Service(item='USB_Cable_Pres', parameters={}, labels=[]),
            Service(item='Stor_Adapt_Pres', parameters={}, labels=[]),
            Service(item='C_Riser_Pres', parameters={}, labels=[]),
            Service(item='L_Riser_Pres', parameters={}, labels=[]),
            Service(item='Presence', parameters={}, labels=[]),
            Service(item='Status', parameters={}, labels=[]),
            Service(item='OS_Watchdog', parameters={}, labels=[]),
            Service(item='Intrusion', parameters={}, labels=[]),
            Service(item='PS_Redundancy', parameters={}, labels=[]),
            Service(item='Fan_Redundancy', parameters={}, labels=[]),
            Service(item='Power_Optimized', parameters={}, labels=[]),
            Service(item='Drive', parameters={}, labels=[]),
            Service(item='Cable_SAS_A', parameters={}, labels=[]),
            Service(item='Cable_SAS_B', parameters={}, labels=[]),
            Service(item='DKM_Status', parameters={}, labels=[]),
            Service(item='VFlash', parameters={}, labels=[]),
            Service(item='PS3_Status', parameters={}, labels=[]),
            Service(item='PS4_Status', parameters={}, labels=[]),
            Service(item='Pwr_Unit_Stat', parameters={}, labels=[]),
            Service(item='Power_Redundancy', parameters={}, labels=[]),
            Service(item='BMC_Watchdog', parameters={}, labels=[]),
            Service(item='PS1_Status', parameters={}, labels=[]),
            Service(item='PS2_Status', parameters={}, labels=[]),
            Service(item='Drive_4', parameters={}, labels=[]),
            Service(item='Ambient', parameters={}, labels=[]),
            Service(item='Systemboard', parameters={}, labels=[]),
            Service(item='CPU', parameters={}, labels=[]),
            Service(item='MEM_A', parameters={}, labels=[]),
            Service(item='MEM_B', parameters={}, labels=[]),
            Service(item='PSU1_Inlet', parameters={}, labels=[]),
            Service(item='PSU2_Inlet', parameters={}, labels=[]),
            Service(item='PSU1', parameters={}, labels=[]),
            Service(item='PSU2', parameters={}, labels=[]),
            Service(item='BATT_3.0V', parameters={}, labels=[]),
            Service(item='STBY_3.3V', parameters={}, labels=[]),
            Service(item='iRMC_1.8V_STBY', parameters={}, labels=[]),
            Service(item='iRMC_1.5V_STBY', parameters={}, labels=[]),
            Service(item='iRMC_1.0V_STBY', parameters={}, labels=[]),
            Service(item='MAIN_12V', parameters={}, labels=[]),
            Service(item='MAIN_5V', parameters={}, labels=[]),
            Service(item='MAIN_3.3V', parameters={}, labels=[]),
            Service(item='MEM_1.35V', parameters={}, labels=[]),
            Service(item='PCH_1.05V', parameters={}, labels=[]),
            Service(item='MEM_VTT_0.68V', parameters={}, labels=[]),
            Service(item='FAN1_SYS', parameters={}, labels=[]),
            Service(item='FAN2_SYS', parameters={}, labels=[]),
            Service(item='FAN3_SYS', parameters={}, labels=[]),
            Service(item='FAN4_SYS', parameters={}, labels=[]),
            Service(item='FAN5_SYS', parameters={}, labels=[]),
            Service(item='FAN_PSU1', parameters={}, labels=[]),
            Service(item='FAN_PSU2', parameters={}, labels=[]),
            Service(item='PSU1_Power', parameters={}, labels=[]),
            Service(item='PSU2_Power', parameters={}, labels=[]),
            Service(item='Total_Power', parameters={}, labels=[]),
            Service(item='Total_Power_Out', parameters={}, labels=[]),
            Service(item='I2C1_error_ratio', parameters={}, labels=[]),
            Service(item='I2C2_error_ratio', parameters={}, labels=[]),
            Service(item='I2C3_error_ratio', parameters={}, labels=[]),
            Service(item='I2C4_error_ratio', parameters={}, labels=[]),
            Service(item='I2C5_error_ratio', parameters={}, labels=[]),
            Service(item='I2C6_error_ratio', parameters={}, labels=[]),
            Service(item='I2C7_error_ratio', parameters={}, labels=[]),
            Service(item='I2C8_error_ratio', parameters={}, labels=[]),
            Service(item='SEL_Level', parameters={}, labels=[]),
        ],
    ),
    (
        {
            "discovery_mode": (
                "single",
                {
                    "ignored_sensorstates": ["ok", "ns", "nc"]
                },
            )
        },
        [],
    ),
])
def test_regression_discovery(
    discovery_params: ipmi_utils.DiscoveryParams,
    discovery_results: DiscoveryResult,
) -> None:
    assert list(ipmi.discover_ipmi(
        discovery_params,
        SECTION_IPMI,
        SECTION_IPMI_DISCRETE,
    )) == discovery_results


@pytest.mark.parametrize(
    "item, check_results",
    [
        (
            "Summary",
            [
                Metric("ambient_temp", 18.5),
                Result(state=State.OK, summary="147 sensors in total"),
                Result(state=State.OK, summary="104 sensors ok"),
                Result(
                    state=State.OK,
                    notice="CMOS_Battery: ok",
                    details="CMOS_Battery: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="ROMB_Battery: ok",
                    details="ROMB_Battery: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="VCORE: ok (State Deasserted)",
                    details=
                    "VCORE: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="1.2V_VDDR: ok (State Deasserted)",
                    details=
                    "1.2V_VDDR: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="VR_1.8V_AUX_PG: ok (State Deasserted)",
                    details=
                    "VR_1.8V_AUX_PG: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="VR_1.2V_AUX_PG: ok (State Deasserted)",
                    details=
                    "VR_1.2V_AUX_PG: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="1.2V_LOM_PG: ok (State Deasserted)",
                    details=
                    "1.2V_LOM_PG: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="8V_PG: ok (State Deasserted)",
                    details=
                    "8V_PG: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="1.2V_AUX_LOM_PG: ok (State Deasserted)",
                    details=
                    "1.2V_AUX_LOM_PG: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="5V_IO_PG: ok (State Deasserted)",
                    details=
                    "5V_IO_PG: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="5V_CPU_PG: ok (State Deasserted)",
                    details=
                    "5V_CPU_PG: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="3.3V_PG: ok (State Deasserted)",
                    details=
                    "3.3V_PG: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="1.8V_PG: ok (State Deasserted)",
                    details=
                    "1.8V_PG: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="1.1V_PG: ok (State Deasserted)",
                    details=
                    "1.1V_PG: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="Mem1_0.75V_PG: ok (State Deasserted)",
                    details=
                    "Mem1_0.75V_PG: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="Mem2_0.75V_PG: ok (State Deasserted)",
                    details=
                    "Mem2_0.75V_PG: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="Mem3_0.75V_PG: ok (State Deasserted)",
                    details=
                    "Mem3_0.75V_PG: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="Mem4_0.75V_PG: ok (State Deasserted)",
                    details=
                    "Mem4_0.75V_PG: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="Mem5_0.75V_PG: ok (State Deasserted)",
                    details=
                    "Mem5_0.75V_PG: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="Mem6_0.75V_PG: ok (State Deasserted)",
                    details=
                    "Mem6_0.75V_PG: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="Mem7_0.75V_PG: ok (State Deasserted)",
                    details=
                    "Mem7_0.75V_PG: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="Mem8_0.75V_PG: ok (State Deasserted)",
                    details=
                    "Mem8_0.75V_PG: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="VR_PLX_PG: ok (State Deasserted)",
                    details=
                    "VR_PLX_PG: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="VR_1.2V_NBSB_PG: ok (State Deasserted)",
                    details=
                    "VR_1.2V_NBSB_PG: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="VR_2.5V_CPU1: ok (State Deasserted)",
                    details=
                    "VR_2.5V_CPU1: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="VR_2.5V_CPU2: ok (State Deasserted)",
                    details=
                    "VR_2.5V_CPU2: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="VR_2.5V_CPU3: ok (State Deasserted)",
                    details=
                    "VR_2.5V_CPU3: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="VR_2.5V_CPU4: ok (State Deasserted)",
                    details=
                    "VR_2.5V_CPU4: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="VR_1.2V_CPU1: ok (State Deasserted)",
                    details=
                    "VR_1.2V_CPU1: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="VR_1.2V_CPU2: ok (State Deasserted)",
                    details=
                    "VR_1.2V_CPU2: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="VR_1.2V_CPU3: ok (State Deasserted)",
                    details=
                    "VR_1.2V_CPU3: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="VR_1.2V_CPU4: ok (State Deasserted)",
                    details=
                    "VR_1.2V_CPU4: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="VR_1.5V_MEM1: ok (State Deasserted)",
                    details=
                    "VR_1.5V_MEM1: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="VR_1.5V_MEM2: ok (State Deasserted)",
                    details=
                    "VR_1.5V_MEM2: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="VR_1.5V_MEM3: ok (State Deasserted)",
                    details=
                    "VR_1.5V_MEM3: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="VR_1.5V_MEM4: ok (State Deasserted)",
                    details=
                    "VR_1.5V_MEM4: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="VR_PSI_MEM1: ok (State Deasserted)",
                    details=
                    "VR_PSI_MEM1: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="VR_PSI_MEM2: ok (State Deasserted)",
                    details=
                    "VR_PSI_MEM2: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="VR_PSI_MEM3: ok (State Deasserted)",
                    details=
                    "VR_PSI_MEM3: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="VR_PSI_MEM4: ok (State Deasserted)",
                    details=
                    "VR_PSI_MEM4: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="Heatsink_Pres: ok (Present)",
                    details="Heatsink_Pres: ok (Present) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="iDRAC6_Ent_Pres: ok (Present)",
                    details=
                    "iDRAC6_Ent_Pres: ok (Present) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="USB_Cable_Pres: ok (Present)",
                    details=
                    "USB_Cable_Pres: ok (Present) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="Stor_Adapt_Pres: ok (Present)",
                    details=
                    "Stor_Adapt_Pres: ok (Present) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="C_Riser_Pres: ok (Present)",
                    details="C_Riser_Pres: ok (Present) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="L_Riser_Pres: ok (Present)",
                    details="L_Riser_Pres: ok (Present) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="Presence: ok (Present)",
                    details="Presence: ok (Present) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="Status: ok (Presence detected)",
                    details=
                    "Status: ok (Presence detected) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="Riser_Config: ok (Connected)",
                    details=
                    "Riser_Config: ok (Connected) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="OS_Watchdog: ok",
                    details="OS_Watchdog: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="Intrusion: ok",
                    details="Intrusion: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="PS_Redundancy: ok (Fully Redundant)",
                    details=
                    "PS_Redundancy: ok (Fully Redundant) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="Fan_Redundancy: ok (Fully Redundant)",
                    details=
                    "Fan_Redundancy: ok (Fully Redundant) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="Power_Optimized: ok (OEM Specific)",
                    details=
                    "Power_Optimized: ok (OEM Specific) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="Drive: ok (Drive Present)",
                    details="Drive: ok (Drive Present) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="Cable_SAS_A: ok (Connected)",
                    details="Cable_SAS_A: ok (Connected) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="Cable_SAS_B: ok (Connected)",
                    details="Cable_SAS_B: ok (Connected) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="DKM_Status: ok",
                    details="DKM_Status: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="VFlash: ok",
                    details="VFlash: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="PS3_Status: ok (Presence detected)",
                    details=
                    "PS3_Status: ok (Presence detected) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="PS4_Status: ok (Presence detected)",
                    details=
                    "PS4_Status: ok (Presence detected) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="Pwr_Unit_Stat: ok",
                    details="Pwr_Unit_Stat: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="Power_Redundancy: ok (Fully Redundant)",
                    details=
                    "Power_Redundancy: ok (Fully Redundant) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="BMC_Watchdog: ok",
                    details="BMC_Watchdog: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="PS2_Status: ok (Presence detected)",
                    details=
                    "PS2_Status: ok (Presence detected) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="Ambient: ok",
                    details="Ambient: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="Systemboard: ok",
                    details="Systemboard: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="CPU: ok",
                    details="CPU: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="MEM_A: ok",
                    details="MEM_A: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="MEM_B: ok",
                    details="MEM_B: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="PSU1_Inlet: ok",
                    details="PSU1_Inlet: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="PSU2_Inlet: ok",
                    details="PSU2_Inlet: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="PSU1: ok",
                    details="PSU1: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="PSU2: ok",
                    details="PSU2: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="BATT_3.0V: ok",
                    details="BATT_3.0V: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="STBY_3.3V: ok",
                    details="STBY_3.3V: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="iRMC_1.8V_STBY: ok",
                    details="iRMC_1.8V_STBY: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="iRMC_1.5V_STBY: ok",
                    details="iRMC_1.5V_STBY: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="iRMC_1.0V_STBY: ok",
                    details="iRMC_1.0V_STBY: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="MAIN_12V: ok",
                    details="MAIN_12V: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="MAIN_5V: ok",
                    details="MAIN_5V: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="MAIN_3.3V: ok",
                    details="MAIN_3.3V: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="MEM_1.35V: ok",
                    details="MEM_1.35V: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="PCH_1.05V: ok",
                    details="PCH_1.05V: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="MEM_VTT_0.68V: ok",
                    details="MEM_VTT_0.68V: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="FAN1_SYS: ok",
                    details="FAN1_SYS: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="FAN2_SYS: ok",
                    details="FAN2_SYS: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="FAN3_SYS: ok",
                    details="FAN3_SYS: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="FAN4_SYS: ok",
                    details="FAN4_SYS: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="FAN_PSU1: ok",
                    details="FAN_PSU1: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="FAN_PSU2: ok",
                    details="FAN_PSU2: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="PSU1_Power: ok",
                    details="PSU1_Power: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="PSU2_Power: ok",
                    details="PSU2_Power: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="Total_Power: ok",
                    details="Total_Power: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="Total_Power_Out: ok",
                    details="Total_Power_Out: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="I2C1_error_ratio: ok",
                    details="I2C1_error_ratio: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="I2C2_error_ratio: ok",
                    details="I2C2_error_ratio: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="I2C3_error_ratio: ok",
                    details="I2C3_error_ratio: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="I2C4_error_ratio: ok",
                    details="I2C4_error_ratio: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="I2C5_error_ratio: ok",
                    details="I2C5_error_ratio: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="I2C6_error_ratio: ok",
                    details="I2C6_error_ratio: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="I2C7_error_ratio: ok",
                    details="I2C7_error_ratio: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="I2C8_error_ratio: ok",
                    details="I2C8_error_ratio: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="SEL_Level: ok",
                    details="SEL_Level: ok (service state derived from sensor events)",
                ),
                Result(state=State.WARN, summary="1 sensors warning"),
                Result(
                    state=State.WARN,
                    notice="FAN5_SYS: nc",
                    details="FAN5_SYS: nc (service state derived from sensor events)",
                ),
                Result(state=State.CRIT, summary="2 sensors critical"),
                Result(
                    state=State.CRIT,
                    notice="PS1_Status: ok (Presence detected, Failure detected)",
                    details=
                    "PS1_Status: ok (Presence detected, Failure detected) (service state derived from sensor events)",
                ),
                Result(
                    state=State.CRIT,
                    notice="Drive_4: ok (Drive Present, Drive Fault)",
                    details=
                    "Drive_4: ok (Drive Present, Drive Fault) (service state derived from sensor events)",
                ),
                Result(state=State.OK, summary="40 sensors skipped"),
                Result(
                    state=State.OK,
                    notice="NB_THERMTRIP: ns (Disabled)",
                ),
                Result(
                    state=State.OK,
                    notice="PFault_Fail_Safe: ns (No Reading)",
                ),
                Result(
                    state=State.OK,
                    notice="SEL: ns (No Reading)",
                ),
                Result(
                    state=State.OK,
                    notice="SD1_Status: ns (Disabled)",
                ),
                Result(
                    state=State.OK,
                    notice="SD2_Status: ns (Disabled)",
                ),
                Result(
                    state=State.OK,
                    notice="SD_Redundancy: ns (Disabled)",
                ),
                Result(
                    state=State.OK,
                    notice="ECC_Corr_Err: ns (No Reading)",
                ),
                Result(
                    state=State.OK,
                    notice="ECC_Uncorr_Err: ns (No Reading)",
                ),
                Result(
                    state=State.OK,
                    notice="I/O_Channel_Chk: ns (No Reading)",
                ),
                Result(
                    state=State.OK,
                    notice="PCI_Parity_Err: ns (No Reading)",
                ),
                Result(
                    state=State.OK,
                    notice="PCI_System_Err: ns (No Reading)",
                ),
                Result(
                    state=State.OK,
                    notice="SBE_Log_Disabled: ns (No Reading)",
                ),
                Result(
                    state=State.OK,
                    notice="Logging_Disabled: ns (No Reading)",
                ),
                Result(
                    state=State.OK,
                    notice="Unknown: ns (No Reading)",
                ),
                Result(
                    state=State.OK,
                    notice="CPU_Protocol_Err: ns (No Reading)",
                ),
                Result(
                    state=State.OK,
                    notice="CPU_Bus_PERR: ns (No Reading)",
                ),
                Result(
                    state=State.OK,
                    notice="CPU_Init_Err: ns (No Reading)",
                ),
                Result(
                    state=State.OK,
                    notice="CPU_Machine_Chk: ns (No Reading)",
                ),
                Result(
                    state=State.OK,
                    notice="Memory_Spared: ns (No Reading)",
                ),
                Result(
                    state=State.OK,
                    notice="Memory_Mirrored: ns (No Reading)",
                ),
                Result(
                    state=State.OK,
                    notice="Memory_RAID: ns (No Reading)",
                ),
                Result(
                    state=State.OK,
                    notice="Memory_Added: ns (No Reading)",
                ),
                Result(
                    state=State.OK,
                    notice="Memory_Removed: ns (No Reading)",
                ),
                Result(
                    state=State.OK,
                    notice="Memory_Cfg_Err: ns (No Reading)",
                ),
                Result(
                    state=State.OK,
                    notice="Mem_Redun_Gain: ns (No Reading)",
                ),
                Result(
                    state=State.OK,
                    notice="PCIE_Fatal_Err: ns (No Reading)",
                ),
                Result(
                    state=State.OK,
                    notice="Chipset_Err: ns (No Reading)",
                ),
                Result(
                    state=State.OK,
                    notice="Err_Reg_Pointer: ns (No Reading)",
                ),
                Result(
                    state=State.OK,
                    notice="Mem_ECC_Warning: ns (No Reading)",
                ),
                Result(
                    state=State.OK,
                    notice="Mem_CRC_Err: ns (No Reading)",
                ),
                Result(
                    state=State.OK,
                    notice="USB_Over-current: ns (No Reading)",
                ),
                Result(
                    state=State.OK,
                    notice="POST_Err: ns (No Reading)",
                ),
                Result(
                    state=State.OK,
                    notice="Hdwr_version_err: ns (No Reading)",
                ),
                Result(
                    state=State.OK,
                    notice="Mem_Overtemp: ns (No Reading)",
                ),
                Result(
                    state=State.OK,
                    notice="Mem_Fatal_SB_CRC: ns (No Reading)",
                ),
                Result(
                    state=State.OK,
                    notice="Mem_Fatal_NB_CRC: ns (No Reading)",
                ),
                Result(
                    state=State.OK,
                    notice="OS_Watchdog_Time: ns (No Reading)",
                ),
                Result(
                    state=State.OK,
                    notice="Non_Fatal_PCI_Er: ns (No Reading)",
                ),
                Result(
                    state=State.OK,
                    notice="Fatal_IO_Error: ns (No Reading)",
                ),
                Result(
                    state=State.OK,
                    notice="MSR_Info_Log: ns (No Reading)",
                ),
            ],
        ),
        (
            "CMOS_Battery",
            [
                Result(
                    state=State.OK,
                    summary="Status: ok",
                    details="Status: ok (service state derived from sensor events)",
                )
            ],
        ),
        (
            "VR_PSI_MEM3",
            [
                Result(
                    state=State.OK,
                    summary="Status: ok (State Deasserted)",
                    details=
                    "Status: ok (State Deasserted) (service state derived from sensor events)",
                )
            ],
        ),
        (
            "Drive",
            [
                Result(
                    state=State.OK,
                    summary="Status: ok (Drive Present)",
                    details="Status: ok (Drive Present) (service state derived from sensor events)",
                )
            ],
        ),
        (
            "Cable_SAS_A",
            [
                Result(
                    state=State.OK,
                    summary="Status: ok (Connected)",
                    details="Status: ok (Connected) (service state derived from sensor events)",
                )
            ],
        ),
        (
            "Power_Redundancy",
            [
                Result(
                    state=State.OK,
                    summary="Status: ok (Fully Redundant)",
                    details=
                    "Status: ok (Fully Redundant) (service state derived from sensor events)",
                )
            ],
        ),
        (
            "PS1_Status",
            [
                Result(
                    state=State.CRIT,
                    summary="Status: ok (Presence detected, Failure detected)",
                    details=
                    "Status: ok (Presence detected, Failure detected) (service state derived from sensor events)",
                )
            ],
        ),
        (
            "Ambient",
            [
                Result(
                    state=State.OK,
                    summary="Status: ok",
                    details="Status: ok (service state derived from sensor events)",
                ),
                Result(state=State.OK, summary="18.50 degrees_C"),
                Metric("Ambient", 18.5, levels=(37.0, 42.0)),
            ],
        ),
        (
            "PSU2",
            [
                Result(
                    state=State.OK,
                    summary="Status: ok",
                    details="Status: ok (service state derived from sensor events)",
                ),
                Result(state=State.OK, summary="58.00 degrees_C"),
                Metric("PSU2", 58.0, levels=(102.0, 107.0)),
            ],
        ),
        (
            "MEM_1.35V",
            [
                Result(
                    state=State.OK,
                    summary="Status: ok",
                    details="Status: ok (service state derived from sensor events)",
                ),
                Result(state=State.OK, summary="1.36 Volts"),
                Metric("MEM_1.35V", 1.36, levels=(None, 1.61)),
            ],
        ),
        (
            "FAN1_SYS",
            [
                Result(
                    state=State.OK,
                    summary="Status: ok",
                    details="Status: ok (service state derived from sensor events)",
                ),
                Result(state=State.OK, summary="5160.00 RPM"),
                Metric("FAN1_SYS", 5160.0),
            ],
        ),
        (
            "Total_Power",
            [
                Result(
                    state=State.OK,
                    summary="Status: ok",
                    details="Status: ok (service state derived from sensor events)",
                ),
                Result(state=State.OK, summary="48.00 Watts"),
                Metric("Total_Power", 48.0, levels=(None, 498.0)),
            ],
        ),
        (
            "I2C8_error_ratio",
            [
                Result(
                    state=State.OK,
                    summary="Status: ok",
                    details="Status: ok (service state derived from sensor events)",
                ),
                Result(state=State.OK, summary="0.00 %"),
                Metric("I2C8_error_ratio", 0.0, levels=(10.0, 20.0)),
            ],
        ),
        (
            "SEL_Level",
            [
                Result(
                    state=State.OK,
                    summary="Status: ok",
                    details="Status: ok (service state derived from sensor events)",
                ),
                Result(state=State.OK, summary="0.00 %"),
                Metric("SEL_Level", 0.0, levels=(90.0, None)),
            ],
        ),
        (
            "Drive_4",
            [
                Result(
                    state=State.CRIT,
                    summary="Status: ok (Drive Present, Drive Fault)",
                    details=
                    "Status: ok (Drive Present, Drive Fault) (service state derived from sensor events)",
                )
            ],
        ),
    ],
)
def test_regression_check(
    item: str,
    check_results: CheckResult,
) -> None:
    assert list(
        ipmi.check_ipmi(
            item,
            {"ignored_sensorstates": ["ns", "nr", "na"]},
            SECTION_IPMI,
            SECTION_IPMI_DISCRETE,
        )) == check_results
