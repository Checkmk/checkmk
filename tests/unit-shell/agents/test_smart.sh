#!/bin/bash
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# shellcheck disable=SC2034
# shellcheck source=agents/plugins/smart
MK_SOURCE_ONLY=true source "${UNIT_SH_PLUGINS_DIR}/smart"

setup_nvme() {
    BY_ID_PATH="${SHUNIT_TMPDIR}/by-id"
    mkdir "$BY_ID_PATH"
    touch "${BY_ID_PATH}/nvme0n1"
    ln -s "${BY_ID_PATH}/nvme0n1" "${BY_ID_PATH}/nvme-KXG8AZNV512G_NVMe_SED_KIOXIA_512GB_92UC8190E0MK"

    BLOCK_PATH="$SHUNIT_TMPDIR/block"
    mkdir -p "$BLOCK_PATH/nvme0n1/device/device/vendor"
    touch "$BLOCK_PATH/nvme0n1/device/model"
    echo "KXG8AZNV512G NVMe SED KIOXIA 512GB" >"$BLOCK_PATH/nvme0n1/device/model"
}

setup_sat() {
    BY_ID_PATH="${SHUNIT_TMPDIR}/by-id"
    mkdir "$BY_ID_PATH"
    touch "${BY_ID_PATH}/WDC_WUH722222ALE6L4_123456A"
    ln -s "${BY_ID_PATH}/WDC_WUH722222ALE6L4_123456A" "${BY_ID_PATH}/ata-WDC_WUH722222ALE6L4_123456A"

    BLOCK_PATH="$SHUNIT_TMPDIR/block"
    mkdir -p "$BLOCK_PATH/WDC_WUH722222ALE6L4_123456A/device"
    touch "$BLOCK_PATH/WDC_WUH722222ALE6L4_123456A/device/model"
    echo "WDC__WUH722222AL" >"$BLOCK_PATH/WDC_WUH722222ALE6L4_123456A/device/model"
}

teardown_test() {
    rm -R "${SHUNIT_TMPDIR}/by-id"
    rm -R "${SHUNIT_TMPDIR}/block"
}

nvme_output() {
    echo 'smartctl 7.2 2020-12-30 r5155 [x86_64-linux-6.8.0-40-generic] (local build)
Copyright (C) 2002-20, Bruce Allen, Christian Franke, www.smartmontools.org

=== START OF SMART DATA SECTION ===
SMART/Health Information (NVMe Log 0x02)
Critical Warning:                   0x00
Temperature:                        39 Celsius
Available Spare:                    100%
Available Spare Threshold:          50%
Percentage Used:                    2%
Data Units Read:                    6,519,237 [3.33 TB]
Data Units Written:                 13,052,641 [6.68 TB]
Host Read Commands:                 111,755,959
Host Write Commands:                318,219,864
Controller Busy Time:               484
Power Cycles:                       205
Power On Hours:                     5,680
Unsafe Shutdowns:                   47
Media and Data Integrity Errors:    0
Error Information Log Entries:      0
Warning  Comp. Temperature Time:    0
Critical Comp. Temperature Time:    0
Temperature Sensor 1:               39 Celsius'
}

sat_output() {
    echo 'smartctl 7.3 2022-02-28 r5338 [x86_64-linux-6.1.0-22-amd64] (local build)
Copyright (C) 2002-22, Bruce Allen, Christian Franke, www.smartmontools.org

=== START OF READ SMART DATA SECTION ===
SMART Attributes Data Structure revision number: 16
Vendor Specific SMART Attributes with Thresholds:
ID# ATTRIBUTE_NAME          FLAG     VALUE WORST THRESH TYPE      UPDATED  WHEN_FAILED RAW_VALUE
  1 Raw_Read_Error_Rate     0x000b   100   100   001    Pre-fail  Always       -       0
  2 Throughput_Performance  0x0005   148   148   054    Pre-fail  Offline      -       49
  3 Spin_Up_Time            0x0007   083   083   001    Pre-fail  Always       -       362 (Average 362)
  4 Start_Stop_Count        0x0012   100   100   000    Old_age   Always       -       7
  5 Reallocated_Sector_Ct   0x0033   100   100   001    Pre-fail  Always       -       0
  7 Seek_Error_Rate         0x000b   100   100   001    Pre-fail  Always       -       0
  8 Seek_Time_Performance   0x0005   140   140   020    Pre-fail  Offline      -       15
  9 Power_On_Hours          0x0012   100   100   000    Old_age   Always       -       362
 10 Spin_Retry_Count        0x0013   100   100   001    Pre-fail  Always       -       0
 12 Power_Cycle_Count       0x0032   100   100   000    Old_age   Always       -       7
 22 Unknown_Attribute       0x0023   100   100   025    Pre-fail  Always       -       6553700
 71 Unknown_Attribute       0x0001   100   100   001    Pre-fail  Offline      -       0
 90 Unknown_Attribute       0x0031   100   100   001    Pre-fail  Offline      -       541165879296
192 Power-Off_Retract_Count 0x0032   100   100   000    Old_age   Always       -       111
193 Load_Cycle_Count        0x0012   100   100   000    Old_age   Always       -       111
194 Temperature_Celsius     0x0002   059   059   000    Old_age   Always       -       39 (Min/Max 22/41)
196 Reallocated_Event_Count 0x0032   100   100   000    Old_age   Always       -       0
197 Current_Pending_Sector  0x0022   100   100   000    Old_age   Always       -       0
198 Offline_Uncorrectable   0x0008   100   100   000    Old_age   Offline      -       0
199 UDMA_CRC_Error_Count    0x000a   100   100   000    Old_age   Always       -       0'
}

smartctl() {
    if [ "$1" == "-d" ] && [ "$2" == "sat" ]; then
        sat_output
    elif [ "$1" == "-d" ] && [ "$2" == "nvme" ]; then
        nvme_output
    fi
}

tw_cli=
MegaCli=
MegaCli64=
megacli=

test_nvme() {
    EXPECTED_OUTPUT="<<<smart>>>
/dev/nvme0n1 NVME KXG8AZNV512G_NVMe_SED_KIOXIA_512GB
Critical Warning:                   0x00
Temperature:                        39 Celsius
Available Spare:                    100%
Available Spare Threshold:          50%
Percentage Used:                    2%
Data Units Read:                    6,519,237 [3.33 TB]
Data Units Written:                 13,052,641 [6.68 TB]
Host Read Commands:                 111,755,959
Host Write Commands:                318,219,864
Controller Busy Time:               484
Power Cycles:                       205
Power On Hours:                     5,680
Unsafe Shutdowns:                   47
Media and Data Integrity Errors:    0
Error Information Log Entries:      0
Warning  Comp. Temperature Time:    0
Critical Comp. Temperature Time:    0
Temperature Sensor 1:               39 Celsius"

    setup_nvme
    assertEquals "$EXPECTED_OUTPUT" "$(main)"
    teardown_test
}

test_sat() {
    EXPECTED_OUTPUT="<<<smart>>>
WDC_WUH722222ALE6L4_123456A ATA WDC__WUH722222AL   1 Raw_Read_Error_Rate     0x000b   100   100   001    Pre-fail  Always       -       0
WDC_WUH722222ALE6L4_123456A ATA WDC__WUH722222AL   3 Spin_Up_Time            0x0007   083   083   001    Pre-fail  Always       -       362 (Average 362)
WDC_WUH722222ALE6L4_123456A ATA WDC__WUH722222AL   4 Start_Stop_Count        0x0012   100   100   000    Old_age   Always       -       7
WDC_WUH722222ALE6L4_123456A ATA WDC__WUH722222AL   5 Reallocated_Sector_Ct   0x0033   100   100   001    Pre-fail  Always       -       0
WDC_WUH722222ALE6L4_123456A ATA WDC__WUH722222AL   7 Seek_Error_Rate         0x000b   100   100   001    Pre-fail  Always       -       0
WDC_WUH722222ALE6L4_123456A ATA WDC__WUH722222AL   9 Power_On_Hours          0x0012   100   100   000    Old_age   Always       -       362
WDC_WUH722222ALE6L4_123456A ATA WDC__WUH722222AL  10 Spin_Retry_Count        0x0013   100   100   001    Pre-fail  Always       -       0
WDC_WUH722222ALE6L4_123456A ATA WDC__WUH722222AL  12 Power_Cycle_Count       0x0032   100   100   000    Old_age   Always       -       7
WDC_WUH722222ALE6L4_123456A ATA WDC__WUH722222AL  22 Unknown_Attribute       0x0023   100   100   025    Pre-fail  Always       -       6553700
WDC_WUH722222ALE6L4_123456A ATA WDC__WUH722222AL 192 Power-Off_Retract_Count 0x0032   100   100   000    Old_age   Always       -       111
WDC_WUH722222ALE6L4_123456A ATA WDC__WUH722222AL 193 Load_Cycle_Count        0x0012   100   100   000    Old_age   Always       -       111
WDC_WUH722222ALE6L4_123456A ATA WDC__WUH722222AL 194 Temperature_Celsius     0x0002   059   059   000    Old_age   Always       -       39 (Min/Max 22/41)
WDC_WUH722222ALE6L4_123456A ATA WDC__WUH722222AL 196 Reallocated_Event_Count 0x0032   100   100   000    Old_age   Always       -       0
WDC_WUH722222ALE6L4_123456A ATA WDC__WUH722222AL 197 Current_Pending_Sector  0x0022   100   100   000    Old_age   Always       -       0
WDC_WUH722222ALE6L4_123456A ATA WDC__WUH722222AL 199 UDMA_CRC_Error_Count    0x000a   100   100   000    Old_age   Always       -       0"

    setup_sat
    assertEquals "$EXPECTED_OUTPUT" "$(main)"
    teardown_test

}

# shellcheck disable=SC1090 # Can't follow
. "$UNIT_SH_SHUNIT2"
