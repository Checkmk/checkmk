#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "quanta_voltage"


info = [
    [
        ["1", "3", "Volt_P12V", "12240", "12600", "-99", "-99", "11400"],
        ["2", "3", "Volt_P1V05", "1058", "1200", "1000", "-99", "989"],
        ["3", "3", "Volt_P1V8_AUX", "100", "2000", "1000", "-99", "1705"],
        ["4", "3", "Volt_P3V3", "3370", "3466", "-99", "-99", "3132"],
        ["5", "3", "Volt_P3V3_AUX", "3370", "34000", "-99", "4000", "5000"],
        ["6", "3", "Volt_P3V_BAT", "3161", "38000", "-99", "2000", "1600"],
        ["7", "3", "Volt_P5V", "5009", "5251", "-99", "-99", "4743"],
        ["17", "3", "Volt_SAS_EXP_3V3\x01", "3302", "4000", "3000", "-99", "2958"],
        ["18", "3", "Volt_SAS_EXP_VCC\x01", "3276", "3000", "2800", "-99", "2964"],
    ]
]


discovery = {
    "": [
        ("Volt_P12V", {}),
        ("Volt_P1V05", {}),
        ("Volt_P1V8_AUX", {}),
        ("Volt_P3V3", {}),
        ("Volt_P3V3_AUX", {}),
        ("Volt_P3V_BAT", {}),
        ("Volt_P5V", {}),
        ("Volt_SAS_EXP_3V3", {}),
        ("Volt_SAS_EXP_VCC", {}),
    ]
}


checks = {
    "": [
        (
            "Volt_P12V",
            {},
            [
                (0, "Status: OK", []),
                (0, "12240.00 V", [("voltage", 12240.0, 12600.0, 12600.0, None, None)]),
            ],
        ),
        (
            "Volt_P1V05",
            {},
            [
                (0, "Status: OK", []),
                (
                    1,
                    "1058.00 V (warn/crit at 1000.00 V/1200.00 V)",
                    [("voltage", 1058.0, 1000.0, 1200.0, None, None)],
                ),
            ],
        ),
        (
            "Volt_P1V8_AUX",
            {},
            [
                (0, "Status: OK", []),
                (
                    2,
                    "100.00 V (warn/crit below 1705.00 V/1705.00 V)",
                    [("voltage", 100.0, 1000.0, 2000.0, None, None)],
                ),
            ],
        ),
        (
            "Volt_P3V3",
            {},
            [
                (0, "Status: OK", []),
                (0, "3370.00 V", [("voltage", 3370.0, 3466.0, 3466.0, None, None)]),
            ],
        ),
        (
            "Volt_P3V3_AUX",
            {},
            [
                (0, "Status: OK", []),
                (
                    2,
                    "3370.00 V (warn/crit below 4000.00 V/5000.00 V)",
                    [("voltage", 3370.0, 34000.0, 34000.0, None, None)],
                ),
            ],
        ),
        (
            "Volt_P3V_BAT",
            {},
            [
                (0, "Status: OK", []),
                (0, "3161.00 V", [("voltage", 3161.0, 38000.0, 38000.0, None, None)]),
            ],
        ),
        (
            "Volt_P5V",
            {},
            [
                (0, "Status: OK", []),
                (0, "5009.00 V", [("voltage", 5009.0, 5251.0, 5251.0, None, None)]),
            ],
        ),
        (
            "Volt_SAS_EXP_3V3",
            {},
            [
                (0, "Status: OK", []),
                (
                    1,
                    "3302.00 V (warn/crit at 3000.00 V/4000.00 V)",
                    [("voltage", 3302.0, 3000.0, 4000.0, None, None)],
                ),
            ],
        ),
        (
            "Volt_SAS_EXP_VCC",
            {},
            [
                (0, "Status: OK", []),
                (
                    2,
                    "3276.00 V (warn/crit at 2800.00 V/3000.00 V)",
                    [("voltage", 3276.0, 2800.0, 3000.0, None, None)],
                ),
            ],
        ),
    ]
}
