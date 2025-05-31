#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Primitive python script to check that hash files is minimally correct

# file content should look approximately as:
#
# check_mk_agent.msi 987227B23CA5A75FB8191F19D718E4348F748082AC16C83B48F99F3F2694913F
# cmk-agent-ctl.exe AC3A70412218B6C97345E152D71CB03B11666A03CD7D8221AC63FAE5F8030972
# OpenHardwareMonitorCLI.exe 652A088B5FA4D90C8B4FB4D68E649A80421552D3341B1E194C38D71825D87B43
# OpenHardwareMonitorLib.dll 30A6C1ABDA911CE64315C5E6C94E6F0689B567E0346F73697D60FA09EA8F913C
# check_mk_service32.exe 295ED26953165FEBC07174277572BC0E5BA7C2A3C6414B689C3A6DB69DF2D876
# check_mk_service64.exe 2BED103B091822BEF9940E62C5AF34C1EA5B3B07466379CA5E44CB1810EFAFAF

import sys

expected_files = {
    "mk-sql.exe",
    "mk-oracle.exe",
    "check_mk_agent.msi",
    "check_mk_service32.exe",
    "check_mk_service64.exe",
    "cmk-agent-ctl.exe",
    "OpenHardwareMonitorCLI.exe",
    "OpenHardwareMonitorLib.dll",
}


with open(sys.argv[1]) as inp:
    lines = inp.readlines()
    files = {l.split()[0] for l in lines}
    if {f.lower() for f in expected_files} != {f.lower() for f in files}:
        print(f"MISSING FILE(S) ERROR: {files} not equal to expected {expected_files}")
        sys.exit(1)
    hashes = {l.split()[1] for l in lines}
    if len(hashes) != len(expected_files) or {len(h) for h in hashes} != {64}:
        print(f"WRONG COUNT ERROR: {len(hashes)}")
        sys.exit(1)

sys.exit(0)
