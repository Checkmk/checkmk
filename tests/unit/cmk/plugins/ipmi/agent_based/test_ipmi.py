#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.agent_based.v2 import CheckResult, DiscoveryResult, Metric, Result, Service, State
from cmk.plugins.ipmi.agent_based import ipmi
from cmk.plugins.ipmi.lib import ipmi as ipmi_utils

SECTION_IPMI = ipmi.parse_ipmi(
    [
        ["Ambient", "18.500", "degrees_C", "ok", "na", "1.000", "6.000", "37.000", "42.000", "na"],
        ["Systemboard", "28.000", "degrees_C", "ok", "na", "na", "na", "75.000", "80.000", "na"],
        ["CPU", "33.000", "degrees_C", "ok", "na", "na", "na", "95.000", "99.000", "na"],
        ["MEM_A", "21.000", "degrees_C", "ok", "na", "na", "na", "78.000", "82.000", "na"],
        ["MEM_B", "21.000", "degrees_C", "ok", "na", "na", "na", "78.000", "82.000", "na"],
        ["PSU1_Inlet", "29.000", "degrees_C", "ok", "na", "na", "na", "57.000", "61.000", "na"],
        ["PSU2_Inlet", "28.000", "degrees_C", "ok", "na", "na", "na", "57.000", "61.000", "na"],
        ["PSU1", "56.000", "degrees_C", "ok", "na", "na", "na", "102.000", "107.000", "na"],
        ["PSU2", "58.000", "degrees_C", "ok", "na", "na", "na", "102.000", "107.000", "na"],
        ["BATT_3.0V", "3.270", "Volts", "ok", "na", "2.025", "2.295", "na", "3.495", "na"],
        ["STBY_3.3V", "3.350", "Volts", "ok", "na", "3.033", "na", "na", "3.567", "na"],
        ["iRMC_1.8V_STBY", "1.790", "Volts", "ok", "na", "1.670", "na", "na", "1.930", "na"],
        ["iRMC_1.5V_STBY", "1.500", "Volts", "ok", "na", "1.390", "na", "na", "1.610", "na"],
        ["iRMC_1.0V_STBY", "0.980", "Volts", "ok", "na", "0.930", "na", "na", "1.080", "na"],
        ["MAIN_12V", "12.540", "Volts", "ok", "na", "11.100", "na", "na", "12.960", "na"],
        ["MAIN_5V", "5.212", "Volts", "ok", "na", "4.624", "na", "na", "5.400", "na"],
        ["MAIN_3.3V", "3.333", "Volts", "ok", "na", "3.033", "na", "na", "3.567", "na"],
        ["MEM_1.35V", "1.360", "Volts", "ok", "na", "1.250", "na", "na", "1.610", "na"],
        ["PCH_1.05V", "1.040", "Volts", "ok", "na", "0.970", "na", "na", "1.130", "na"],
        ["MEM_VTT_0.68V", "0.660", "Volts", "ok", "na", "0.630", "na", "na", "0.810", "na"],
        ["FAN1_SYS", "5160.000", "RPM", "ok", "na", "600.000", "na", "na", "na", "na"],
        ["FAN2_SYS", "2400.000", "RPM", "ok", "na", "600.000", "na", "na", "na", "na"],
        ["FAN3_SYS", "2400.000", "RPM", "ok", "na", "600.000", "na", "na", "na", "na"],
        ["FAN4_SYS", "1980.000", "RPM", "ok", "na", "600.000", "na", "na", "na", "na"],
        ["FAN5_SYS", "2280.000", "RPM", "nc", "na", "600.000", "na", "na", "na", "na"],
        ["FAN_PSU1", "2320.000", "RPM", "ok", "na", "400.000", "na", "na", "na", "na"],
        ["FAN_PSU2", "2400.000", "RPM", "ok", "na", "400.000", "na", "na", "na", "na"],
        ["PSU1_Power", "18.000", "Watts", "ok", "na", "na", "na", "na", "na", "na"],
        ["PSU2_Power", "30.000", "Watts", "ok", "na", "na", "na", "na", "na", "na"],
        ["Total_Power", "48.000", "Watts", "ok", "na", "na", "na", "na", "498.000", "na"],
        ["Total_Power_Out", "33.000", "Watts", "ok", "na", "na", "na", "na", "na", "na"],
        ["I2C1_error_ratio", "0.000", "percent", "ok", "na", "na", "na", "10.000", "20.000", "na"],
        ["I2C2_error_ratio", "0.000", "percent", "ok", "na", "na", "na", "10.000", "20.000", "na"],
        ["I2C3_error_ratio", "0.000", "percent", "ok", "na", "na", "na", "10.000", "20.000", "na"],
        ["I2C4_error_ratio", "0.000", "percent", "ok", "na", "na", "na", "10.000", "20.000", "na"],
        ["I2C5_error_ratio", "0.000", "percent", "ok", "na", "na", "na", "10.000", "20.000", "na"],
        ["I2C6_error_ratio", "0.000", "percent", "ok", "na", "na", "na", "10.000", "20.000", "na"],
        ["I2C7_error_ratio", "0.000", "percent", "ok", "na", "na", "na", "10.000", "20.000", "na"],
        ["I2C8_error_ratio", "0.000", "percent", "ok", "na", "na", "na", "10.000", "20.000", "na"],
        ["SEL_Level", "0.000", "percent", "ok", "na", "na", "na", "90.000", "na", "na"],
    ]
)

SECTION_IPMI_DISCRETE = ipmi.parse_ipmi(
    [
        ["CMOS Battery     ", " 10h ", " ok  ", "  7.1 ", ""],
        ["ROMB Battery     ", " 11h ", " ok  ", " 26.3 ", ""],
        ["VCORE            ", " 12h ", " ok  ", "  3.1 ", " State Deasserted"],
        ["VCORE            ", " 13h ", " ok  ", "  3.2 ", " State Deasserted"],
        ["VCORE            ", " 14h ", " ok  ", "  3.3 ", " State Deasserted"],
        ["VCORE            ", " 15h ", " ok  ", "  3.4 ", " State Deasserted"],
        ["1.2V VDDR        ", " 16h ", " ok  ", "  3.1 ", " State Deasserted"],
        ["1.2V VDDR        ", " 17h ", " ok  ", "  3.2 ", " State Deasserted"],
        ["1.2V VDDR        ", " 18h ", " ok  ", "  3.3 ", " State Deasserted"],
        ["1.2V VDDR        ", " 19h ", " ok  ", "  3.4 ", " State Deasserted"],
        ["VR 1.8V AUX PG   ", " 1Ah ", " ok  ", "  7.4 ", " State Deasserted"],
        ["VR 1.2V AUX PG   ", " 1Bh ", " ok  ", "  7.4 ", " State Deasserted"],
        ["1.2V LOM PG      ", " 1Ch ", " ok  ", "  7.4 ", " State Deasserted"],
        ["8V PG            ", " 1Dh ", " ok  ", "  7.1 ", " State Deasserted"],
        ["1.2V AUX LOM PG  ", " 1Eh ", " ok  ", "  7.1 ", " State Deasserted"],
        ["5V IO PG         ", " 1Fh ", " ok  ", "  7.1 ", " State Deasserted"],
        ["5V CPU PG        ", " 20h ", " ok  ", "  7.1 ", " State Deasserted"],
        ["3.3V PG          ", " 21h ", " ok  ", "  7.1 ", " State Deasserted"],
        ["1.8V PG          ", " 22h ", " ok  ", "  7.1 ", " State Deasserted"],
        ["1.1V PG          ", " 24h ", " ok  ", "  7.1 ", " State Deasserted"],
        ["Mem1 0.75V PG    ", " 26h ", " ok  ", "  8.1 ", " State Deasserted"],
        ["Mem2 0.75V PG    ", " 27h ", " ok  ", "  8.2 ", " State Deasserted"],
        ["Mem3 0.75V PG    ", " 28h ", " ok  ", "  8.3 ", " State Deasserted"],
        ["Mem4 0.75V PG    ", " 29h ", " ok  ", "  8.4 ", " State Deasserted"],
        ["Mem5 0.75V PG    ", " 2Ah ", " ok  ", "  8.5 ", " State Deasserted"],
        ["Mem6 0.75V PG    ", " 2Bh ", " ok  ", "  8.6 ", " State Deasserted"],
        ["Mem7 0.75V PG    ", " 2Ch ", " ok  ", "  8.7 ", " State Deasserted"],
        ["Mem8 0.75V PG    ", " 2Dh ", " ok  ", "  8.8 ", " State Deasserted"],
        ["VR PLX PG        ", " 2Eh ", " ok  ", "  7.8 ", " State Deasserted"],
        ["VR 1.2V NBSB PG  ", " 2Fh ", " ok  ", "  7.8 ", " State Deasserted"],
        ["VR 2.5V CPU1     ", " C0h ", " ok  ", "  9.8 ", " State Deasserted"],
        ["VR 2.5V CPU2     ", " C1h ", " ok  ", "  9.8 ", " State Deasserted"],
        ["VR 2.5V CPU3     ", " C2h ", " ok  ", "  9.8 ", " State Deasserted"],
        ["VR 2.5V CPU4     ", " C3h ", " ok  ", "  9.8 ", " State Deasserted"],
        ["VR 1.2V CPU1     ", " C4h ", " ok  ", "  9.8 ", " State Deasserted"],
        ["VR 1.2V CPU2     ", " C5h ", " ok  ", "  9.8 ", " State Deasserted"],
        ["VR 1.2V CPU3     ", " C6h ", " ok  ", "  9.8 ", " State Deasserted"],
        ["VR 1.2V CPU4     ", " C7h ", " ok  ", "  9.8 ", " State Deasserted"],
        ["VR 1.5V MEM1     ", " C8h ", " ok  ", "  8.8 ", " State Deasserted"],
        ["VR 1.5V MEM2     ", " C9h ", " ok  ", "  8.8 ", " State Deasserted"],
        ["VR 1.5V MEM3     ", " CAh ", " ok  ", "  8.8 ", " State Deasserted"],
        ["VR 1.5V MEM4     ", " CBh ", " ok  ", "  8.8 ", " State Deasserted"],
        ["VR PSI MEM1      ", " CCh ", " ok  ", "  8.8 ", " State Deasserted"],
        ["VR PSI MEM2      ", " CDh ", " ok  ", "  8.8 ", " State Deasserted"],
        ["VR PSI MEM3      ", " CEh ", " ok  ", "  8.8 ", " State Deasserted"],
        ["VR PSI MEM4      ", " CFh ", " ok  ", "  8.8 ", " State Deasserted"],
        ["NB THERMTRIP     ", " A1h ", " ns  ", "  7.1 ", " Disabled"],
        ["PFault Fail Safe ", " 5Fh ", " ns  ", "  7.1 ", " No Reading"],
        ["Heatsink Pres    ", " 5Dh ", " ok  ", "  7.1 ", " Present"],
        ["iDRAC6 Ent Pres  ", " 70h ", " ok  ", "  7.1 ", " Present"],
        ["USB Cable Pres   ", " 59h ", " ok  ", "  7.1 ", " Present"],
        ["Stor Adapt Pres  ", " 5Ah ", " ok  ", "  7.1 ", " Present"],
        ["C Riser Pres     ", " 5Bh ", " ok  ", "  7.1 ", " Present"],
        ["L Riser Pres     ", " 5Ch ", " ok  ", "  7.1 ", " Present"],
        ["Presence         ", " 50h ", " ok  ", "  3.1 ", " Present"],
        ["Presence         ", " 51h ", " ok  ", "  3.2 ", " Present"],
        ["Presence         ", " 52h ", " ok  ", "  3.3 ", " Present"],
        ["Presence         ", " 53h ", " ok  ", "  3.4 ", " Present"],
        ["Presence         ", " 54h ", " ok  ", " 10.1 ", " Present"],
        ["Presence         ", " 55h ", " ok  ", " 10.2 ", " Present"],
        ["Presence         ", " 58h ", " ok  ", " 26.1 ", " Present"],
        ["Status           ", " 60h ", " ok  ", "  3.1 ", " Presence detected"],
        ["Status           ", " 61h ", " ok  ", "  3.2 ", " Presence detected"],
        ["Status           ", " 62h ", " ok  ", "  3.3 ", " Presence detected"],
        ["Status           ", " 63h ", " ok  ", "  3.4 ", " Presence detected"],
        ["Status           ", " 64h ", " ok  ", " 10.1 ", " Presence detected"],
        ["Status           ", " 65h ", " ok  ", " 10.2 ", " Presence detected"],
        ["Riser Config     ", " 68h ", " ok  ", "  7.1 ", " Connected"],
        ["OS Watchdog      ", " 71h ", " ok  ", "  7.1 ", ""],
        ["SEL              ", " 72h ", " ns  ", "  7.1 ", " No Reading"],
        ["Intrusion        ", " 73h ", " ok  ", "  7.1 ", ""],
        ["PS Redundancy    ", " 74h ", " ok  ", "  7.1 ", " Fully Redundant"],
        ["Fan Redundancy   ", " 75h ", " ok  ", "  7.1 ", " Fully Redundant"],
        ["Power Optimized  ", " 99h ", " ok  ", "  7.1 ", " OEM Specific"],
        ["Drive            ", " 80h ", " ok  ", " 26.1 ", " Drive Present"],
        ["Cable SAS A      ", " 90h ", " ok  ", " 26.1 ", " Connected"],
        ["Cable SAS B      ", " 91h ", " ok  ", " 26.1 ", " Connected"],
        ["DKM Status       ", " A0h ", " ok  ", "  7.1 ", ""],
        ["SD1 Status       ", " D0h ", " ns  ", " 11.1 ", " Disabled"],
        ["SD2 Status       ", " D1h ", " ns  ", " 11.1 ", " Disabled"],
        ["SD Redundancy    ", " D2h ", " ns  ", " 11.1 ", " Disabled"],
        ["VFlash           ", " D3h ", " ok  ", " 11.2 ", ""],
        ["ECC Corr Err     ", " 01h ", " ns  ", " 34.1 ", " No Reading"],
        ["ECC Uncorr Err   ", " 02h ", " ns  ", " 34.1 ", " No Reading"],
        ["I/O Channel Chk  ", " 03h ", " ns  ", " 34.1 ", " No Reading"],
        ["PCI Parity Err   ", " 04h ", " ns  ", " 34.1 ", " No Reading"],
        ["PCI System Err   ", " 05h ", " ns  ", " 34.1 ", " No Reading"],
        ["SBE Log Disabled ", " 06h ", " ns  ", " 34.1 ", " No Reading"],
        ["Logging Disabled ", " 07h ", " ns  ", " 34.1 ", " No Reading"],
        ["Unknown          ", " 08h ", " ns  ", " 34.1 ", " No Reading"],
        ["CPU Protocol Err ", " 0Ah ", " ns  ", " 34.1 ", " No Reading"],
        ["CPU Bus PERR     ", " 0Bh ", " ns  ", " 34.1 ", " No Reading"],
        ["CPU Init Err     ", " 0Ch ", " ns  ", " 34.1 ", " No Reading"],
        ["CPU Machine Chk  ", " 0Dh ", " ns  ", " 34.1 ", " No Reading"],
        ["Memory Spared    ", " 11h ", " ns  ", " 34.1 ", " No Reading"],
        ["Memory Mirrored  ", " 12h ", " ns  ", " 34.1 ", " No Reading"],
        ["Memory RAID      ", " 13h ", " ns  ", " 34.1 ", " No Reading"],
        ["Memory Added     ", " 14h ", " ns  ", " 34.1 ", " No Reading"],
        ["Memory Removed   ", " 15h ", " ns  ", " 34.1 ", " No Reading"],
        ["Memory Cfg Err   ", " 16h ", " ns  ", " 34.1 ", " No Reading"],
        ["Mem Redun Gain   ", " 17h ", " ns  ", " 34.1 ", " No Reading"],
        ["PCIE Fatal Err   ", " 18h ", " ns  ", " 34.1 ", " No Reading"],
        ["Chipset Err      ", " 19h ", " ns  ", " 34.1 ", " No Reading"],
        ["Err Reg Pointer  ", " 1Ah ", " ns  ", " 34.1 ", " No Reading"],
        ["Mem ECC Warning  ", " 1Bh ", " ns  ", " 34.1 ", " No Reading"],
        ["Mem CRC Err      ", " 1Ch ", " ns  ", " 34.1 ", " No Reading"],
        ["USB Over-current ", " 1Dh ", " ns  ", " 34.1 ", " No Reading"],
        ["POST Err         ", " 1Eh ", " ns  ", " 34.1 ", " No Reading"],
        ["Hdwr version err ", " 1Fh ", " ns  ", " 34.1 ", " No Reading"],
        ["Mem Overtemp     ", " 20h ", " ns  ", " 34.1 ", " No Reading"],
        ["Mem Fatal SB CRC ", " 21h ", " ns  ", " 34.1 ", " No Reading"],
        ["Mem Fatal NB CRC ", " 22h ", " ns  ", " 34.1 ", " No Reading"],
        ["OS Watchdog Time ", " 23h ", " ns  ", " 34.1 ", " No Reading"],
        ["Non Fatal PCI Er ", " 26h ", " ns  ", " 34.1 ", " No Reading"],
        ["Fatal IO Error   ", " 27h ", " ns  ", " 34.1 ", " No Reading"],
        ["MSR Info Log     ", " 28h ", " ns  ", " 34.1 ", " No Reading"],
        ["PS3 Status       ", " C8h ", " ok ", " 10.1 ", " Presence detected"],
        ["PS4 Status       ", " C9h ", " ok ", " 10.2 ", " Presence detected"],
        ["Pwr Unit Stat    ", " 01h ", " ok ", " 21.1 ", ""],
        ["Power Redundancy ", " 02h ", " ok ", " 21.1 ", " Fully Redundant"],
        ["BMC Watchdog     ", " 03h ", " ok ", "  7.1 ", ""],
        [
            "PS1 Status       ",
            " C8h ",
            " ok ",
            " 10.1 ",
            " Presence detected, Failure detected",
        ],
        ["PS2 Status       ", " C9h ", " ok ", " 10.2 ", " Presence detected"],
        ["Status       ", " C9h ", " ok ", " 10.2 ", " Presence detected"],
        ["Drive 4          ", " 64h ", " ok  ", "  4.4 ", " Drive Present, Drive Fault"],
    ]
)


@pytest.mark.parametrize(
    "discovery_params, discovery_results",
    [
        (
            {"discovery_mode": ("summarize", None)},
            [Service(item="Summary", parameters={}, labels=[])],
        ),
        (
            {
                "discovery_mode": (
                    "single",
                    {"ignored_sensors": ["VR_1.2V_CPU2", "Riser_Config"]},
                ),
            },
            [
                Service(item="CMOS_Battery", parameters={}, labels=[]),
                Service(item="ROMB_Battery", parameters={}, labels=[]),
                Service(item="VCORE", parameters={}, labels=[]),
                Service(item="1.2V_VDDR", parameters={}, labels=[]),
                Service(item="VR_1.8V_AUX_PG", parameters={}, labels=[]),
                Service(item="VR_1.2V_AUX_PG", parameters={}, labels=[]),
                Service(item="1.2V_LOM_PG", parameters={}, labels=[]),
                Service(item="8V_PG", parameters={}, labels=[]),
                Service(item="1.2V_AUX_LOM_PG", parameters={}, labels=[]),
                Service(item="5V_IO_PG", parameters={}, labels=[]),
                Service(item="5V_CPU_PG", parameters={}, labels=[]),
                Service(item="3.3V_PG", parameters={}, labels=[]),
                Service(item="1.8V_PG", parameters={}, labels=[]),
                Service(item="1.1V_PG", parameters={}, labels=[]),
                Service(item="Mem1_0.75V_PG", parameters={}, labels=[]),
                Service(item="Mem2_0.75V_PG", parameters={}, labels=[]),
                Service(item="Mem3_0.75V_PG", parameters={}, labels=[]),
                Service(item="Mem4_0.75V_PG", parameters={}, labels=[]),
                Service(item="Mem5_0.75V_PG", parameters={}, labels=[]),
                Service(item="Mem6_0.75V_PG", parameters={}, labels=[]),
                Service(item="Mem7_0.75V_PG", parameters={}, labels=[]),
                Service(item="Mem8_0.75V_PG", parameters={}, labels=[]),
                Service(item="VR_PLX_PG", parameters={}, labels=[]),
                Service(item="VR_1.2V_NBSB_PG", parameters={}, labels=[]),
                Service(item="VR_2.5V_CPU1", parameters={}, labels=[]),
                Service(item="VR_2.5V_CPU2", parameters={}, labels=[]),
                Service(item="VR_2.5V_CPU3", parameters={}, labels=[]),
                Service(item="VR_2.5V_CPU4", parameters={}, labels=[]),
                Service(item="VR_1.2V_CPU1", parameters={}, labels=[]),
                Service(item="VR_1.2V_CPU3", parameters={}, labels=[]),
                Service(item="VR_1.2V_CPU4", parameters={}, labels=[]),
                Service(item="VR_1.5V_MEM1", parameters={}, labels=[]),
                Service(item="VR_1.5V_MEM2", parameters={}, labels=[]),
                Service(item="VR_1.5V_MEM3", parameters={}, labels=[]),
                Service(item="VR_1.5V_MEM4", parameters={}, labels=[]),
                Service(item="VR_PSI_MEM1", parameters={}, labels=[]),
                Service(item="VR_PSI_MEM2", parameters={}, labels=[]),
                Service(item="VR_PSI_MEM3", parameters={}, labels=[]),
                Service(item="VR_PSI_MEM4", parameters={}, labels=[]),
                Service(item="Heatsink_Pres", parameters={}, labels=[]),
                Service(item="iDRAC6_Ent_Pres", parameters={}, labels=[]),
                Service(item="USB_Cable_Pres", parameters={}, labels=[]),
                Service(item="Stor_Adapt_Pres", parameters={}, labels=[]),
                Service(item="C_Riser_Pres", parameters={}, labels=[]),
                Service(item="L_Riser_Pres", parameters={}, labels=[]),
                Service(item="Presence", parameters={}, labels=[]),
                Service(item="Status", parameters={}, labels=[]),
                Service(item="OS_Watchdog", parameters={}, labels=[]),
                Service(item="Intrusion", parameters={}, labels=[]),
                Service(item="PS_Redundancy", parameters={}, labels=[]),
                Service(item="Fan_Redundancy", parameters={}, labels=[]),
                Service(item="Power_Optimized", parameters={}, labels=[]),
                Service(item="Drive", parameters={}, labels=[]),
                Service(item="Cable_SAS_A", parameters={}, labels=[]),
                Service(item="Cable_SAS_B", parameters={}, labels=[]),
                Service(item="DKM_Status", parameters={}, labels=[]),
                Service(item="VFlash", parameters={}, labels=[]),
                Service(item="PS3_Status", parameters={}, labels=[]),
                Service(item="PS4_Status", parameters={}, labels=[]),
                Service(item="Pwr_Unit_Stat", parameters={}, labels=[]),
                Service(item="Power_Redundancy", parameters={}, labels=[]),
                Service(item="BMC_Watchdog", parameters={}, labels=[]),
                Service(item="PS1_Status", parameters={}, labels=[]),
                Service(item="PS2_Status", parameters={}, labels=[]),
                Service(item="Drive_4", parameters={}, labels=[]),
                Service(item="Ambient", parameters={}, labels=[]),
                Service(item="Systemboard", parameters={}, labels=[]),
                Service(item="CPU", parameters={}, labels=[]),
                Service(item="MEM_A", parameters={}, labels=[]),
                Service(item="MEM_B", parameters={}, labels=[]),
                Service(item="PSU1_Inlet", parameters={}, labels=[]),
                Service(item="PSU2_Inlet", parameters={}, labels=[]),
                Service(item="PSU1", parameters={}, labels=[]),
                Service(item="PSU2", parameters={}, labels=[]),
                Service(item="BATT_3.0V", parameters={}, labels=[]),
                Service(item="STBY_3.3V", parameters={}, labels=[]),
                Service(item="iRMC_1.8V_STBY", parameters={}, labels=[]),
                Service(item="iRMC_1.5V_STBY", parameters={}, labels=[]),
                Service(item="iRMC_1.0V_STBY", parameters={}, labels=[]),
                Service(item="MAIN_12V", parameters={}, labels=[]),
                Service(item="MAIN_5V", parameters={}, labels=[]),
                Service(item="MAIN_3.3V", parameters={}, labels=[]),
                Service(item="MEM_1.35V", parameters={}, labels=[]),
                Service(item="PCH_1.05V", parameters={}, labels=[]),
                Service(item="MEM_VTT_0.68V", parameters={}, labels=[]),
                Service(item="FAN1_SYS", parameters={}, labels=[]),
                Service(item="FAN2_SYS", parameters={}, labels=[]),
                Service(item="FAN3_SYS", parameters={}, labels=[]),
                Service(item="FAN4_SYS", parameters={}, labels=[]),
                Service(item="FAN5_SYS", parameters={}, labels=[]),
                Service(item="FAN_PSU1", parameters={}, labels=[]),
                Service(item="FAN_PSU2", parameters={}, labels=[]),
                Service(item="PSU1_Power", parameters={}, labels=[]),
                Service(item="PSU2_Power", parameters={}, labels=[]),
                Service(item="Total_Power", parameters={}, labels=[]),
                Service(item="Total_Power_Out", parameters={}, labels=[]),
                Service(item="I2C1_error_ratio", parameters={}, labels=[]),
                Service(item="I2C2_error_ratio", parameters={}, labels=[]),
                Service(item="I2C3_error_ratio", parameters={}, labels=[]),
                Service(item="I2C4_error_ratio", parameters={}, labels=[]),
                Service(item="I2C5_error_ratio", parameters={}, labels=[]),
                Service(item="I2C6_error_ratio", parameters={}, labels=[]),
                Service(item="I2C7_error_ratio", parameters={}, labels=[]),
                Service(item="I2C8_error_ratio", parameters={}, labels=[]),
                Service(item="SEL_Level", parameters={}, labels=[]),
            ],
        ),
        (
            {
                "discovery_mode": (
                    "single",
                    {"ignored_sensorstates": ["ok", "ns", "nc"]},
                )
            },
            [],
        ),
    ],
)
def test_regression_discovery(
    discovery_params: ipmi_utils.DiscoveryParams,
    discovery_results: DiscoveryResult,
) -> None:
    assert (
        list(
            ipmi.discover_ipmi(
                discovery_params,
                SECTION_IPMI,
                SECTION_IPMI_DISCRETE,
            )
        )
        == discovery_results
    )


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
                    details="VCORE: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="1.2V_VDDR: ok (State Deasserted)",
                    details="1.2V_VDDR: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="VR_1.8V_AUX_PG: ok (State Deasserted)",
                    details="VR_1.8V_AUX_PG: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="VR_1.2V_AUX_PG: ok (State Deasserted)",
                    details="VR_1.2V_AUX_PG: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="1.2V_LOM_PG: ok (State Deasserted)",
                    details="1.2V_LOM_PG: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="8V_PG: ok (State Deasserted)",
                    details="8V_PG: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="1.2V_AUX_LOM_PG: ok (State Deasserted)",
                    details="1.2V_AUX_LOM_PG: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="5V_IO_PG: ok (State Deasserted)",
                    details="5V_IO_PG: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="5V_CPU_PG: ok (State Deasserted)",
                    details="5V_CPU_PG: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="3.3V_PG: ok (State Deasserted)",
                    details="3.3V_PG: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="1.8V_PG: ok (State Deasserted)",
                    details="1.8V_PG: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="1.1V_PG: ok (State Deasserted)",
                    details="1.1V_PG: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="Mem1_0.75V_PG: ok (State Deasserted)",
                    details="Mem1_0.75V_PG: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="Mem2_0.75V_PG: ok (State Deasserted)",
                    details="Mem2_0.75V_PG: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="Mem3_0.75V_PG: ok (State Deasserted)",
                    details="Mem3_0.75V_PG: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="Mem4_0.75V_PG: ok (State Deasserted)",
                    details="Mem4_0.75V_PG: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="Mem5_0.75V_PG: ok (State Deasserted)",
                    details="Mem5_0.75V_PG: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="Mem6_0.75V_PG: ok (State Deasserted)",
                    details="Mem6_0.75V_PG: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="Mem7_0.75V_PG: ok (State Deasserted)",
                    details="Mem7_0.75V_PG: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="Mem8_0.75V_PG: ok (State Deasserted)",
                    details="Mem8_0.75V_PG: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="VR_PLX_PG: ok (State Deasserted)",
                    details="VR_PLX_PG: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="VR_1.2V_NBSB_PG: ok (State Deasserted)",
                    details="VR_1.2V_NBSB_PG: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="VR_2.5V_CPU1: ok (State Deasserted)",
                    details="VR_2.5V_CPU1: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="VR_2.5V_CPU2: ok (State Deasserted)",
                    details="VR_2.5V_CPU2: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="VR_2.5V_CPU3: ok (State Deasserted)",
                    details="VR_2.5V_CPU3: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="VR_2.5V_CPU4: ok (State Deasserted)",
                    details="VR_2.5V_CPU4: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="VR_1.2V_CPU1: ok (State Deasserted)",
                    details="VR_1.2V_CPU1: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="VR_1.2V_CPU2: ok (State Deasserted)",
                    details="VR_1.2V_CPU2: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="VR_1.2V_CPU3: ok (State Deasserted)",
                    details="VR_1.2V_CPU3: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="VR_1.2V_CPU4: ok (State Deasserted)",
                    details="VR_1.2V_CPU4: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="VR_1.5V_MEM1: ok (State Deasserted)",
                    details="VR_1.5V_MEM1: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="VR_1.5V_MEM2: ok (State Deasserted)",
                    details="VR_1.5V_MEM2: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="VR_1.5V_MEM3: ok (State Deasserted)",
                    details="VR_1.5V_MEM3: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="VR_1.5V_MEM4: ok (State Deasserted)",
                    details="VR_1.5V_MEM4: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="VR_PSI_MEM1: ok (State Deasserted)",
                    details="VR_PSI_MEM1: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="VR_PSI_MEM2: ok (State Deasserted)",
                    details="VR_PSI_MEM2: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="VR_PSI_MEM3: ok (State Deasserted)",
                    details="VR_PSI_MEM3: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="VR_PSI_MEM4: ok (State Deasserted)",
                    details="VR_PSI_MEM4: ok (State Deasserted) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="Heatsink_Pres: ok (Present)",
                    details="Heatsink_Pres: ok (Present) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="iDRAC6_Ent_Pres: ok (Present)",
                    details="iDRAC6_Ent_Pres: ok (Present) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="USB_Cable_Pres: ok (Present)",
                    details="USB_Cable_Pres: ok (Present) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="Stor_Adapt_Pres: ok (Present)",
                    details="Stor_Adapt_Pres: ok (Present) (service state derived from sensor events)",
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
                    details="Status: ok (Presence detected) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="Riser_Config: ok (Connected)",
                    details="Riser_Config: ok (Connected) (service state derived from sensor events)",
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
                    details="PS_Redundancy: ok (Fully Redundant) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="Fan_Redundancy: ok (Fully Redundant)",
                    details="Fan_Redundancy: ok (Fully Redundant) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="Power_Optimized: ok (OEM Specific)",
                    details="Power_Optimized: ok (OEM Specific) (service state derived from sensor events)",
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
                    details="PS3_Status: ok (Presence detected) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="PS4_Status: ok (Presence detected)",
                    details="PS4_Status: ok (Presence detected) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="Pwr_Unit_Stat: ok",
                    details="Pwr_Unit_Stat: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="Power_Redundancy: ok (Fully Redundant)",
                    details="Power_Redundancy: ok (Fully Redundant) (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="BMC_Watchdog: ok",
                    details="BMC_Watchdog: ok (service state derived from sensor events)",
                ),
                Result(
                    state=State.OK,
                    notice="PS2_Status: ok (Presence detected)",
                    details="PS2_Status: ok (Presence detected) (service state derived from sensor events)",
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
                    details="PS1_Status: ok (Presence detected, Failure detected) (service state derived from sensor events)",
                ),
                Result(
                    state=State.CRIT,
                    notice="Drive_4: ok (Drive Present, Drive Fault)",
                    details="Drive_4: ok (Drive Present, Drive Fault) (service state derived from sensor events)",
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
                    details="Status: ok (State Deasserted) (service state derived from sensor events)",
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
                    details="Status: ok (Fully Redundant) (service state derived from sensor events)",
                )
            ],
        ),
        (
            "PS1_Status",
            [
                Result(
                    state=State.CRIT,
                    summary="Status: ok (Presence detected, Failure detected)",
                    details="Status: ok (Presence detected, Failure detected) (service state derived from sensor events)",
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
                Metric("MEM_1.35V", 1.36, levels=(1.61, 1.61)),
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
                Metric("Total_Power", 48.0, levels=(498.0, 498.0)),
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
                Metric("SEL_Level", 0.0),
            ],
        ),
        (
            "Drive_4",
            [
                Result(
                    state=State.CRIT,
                    summary="Status: ok (Drive Present, Drive Fault)",
                    details="Status: ok (Drive Present, Drive Fault) (service state derived from sensor events)",
                )
            ],
        ),
    ],
)
def test_regression_check(
    item: str,
    check_results: CheckResult,
) -> None:
    assert (
        list(
            ipmi.check_ipmi(
                item,
                {"ignored_sensorstates": ["ns", "nr", "na"]},
                SECTION_IPMI,
                SECTION_IPMI_DISCRETE,
            )
        )
        == check_results
    )
