#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated
checkname = "md"

info = [
    ["Personalities", ":", "[raid1]", "[raid6]", "[raid5]", "[raid4]"],
    ["md1", ":", "active", "raid1", "sdb2[0]", "sdd2[1]"],
    ["182751552", "blocks", "super", "1.2", "[2/2]", "[UU]"],
    ["bitmap:", "1/2", "pages", "[4KB],", "65536KB", "chunk"],
    ["md2", ":", "active", "raid5", "sdf1[5]", "sde1[2]", "sdc1[1]", "sdg1[3]", "sda1[0]"],
    [
        "31255568384",
        "blocks",
        "super",
        "1.2",
        "level",
        "5,",
        "512k",
        "chunk,",
        "algorithm",
        "2",
        "[5/5]",
        "[UUUUU]",
    ],
    [
        "[===============>.....]",
        "check",
        "=",
        "76.0%",
        "(5938607824/7813892096)",
        "finish=255.8min",
        "speed=122145K/sec",
    ],
    ["bitmap:", "0/59", "pages", "[0KB],", "65536KB", "chunk"],
    ["md3", ":", "active", "raid1", "sdd1[1]", "sdb1[0]"],
    ["67107840", "blocks", "super", "1.2", "[2/2]", "[UU]"],
    ["bitmap:", "1/1", "pages", "[4KB],", "65536KB", "chunk"],
    ["md4", ":", "active", "raid1", "dm-19[0]", "dm-9[1]"],
    ["20971456", "blocks", "[2/2]", "[UU]"],
    ["20971456", "blocks", "super", "1.2", "[2/2]", "[UU]"],
    ["md5", ":", "active", "(auto-read-only)", "raid1", "sda6[0]", "sdb6[1]"],
    ["4200952", "blocks", "super", "1.0", "[2/2]", "[UU]"],
    ["bitmap:", "0/9", "pages", "[0KB],", "256KB", "chunk"],
    ["md6", ":", "active", "raid5", "sde1[3](S)", "sdd1[0]", "sdg1[2]", "sdf1[1]"],
    ["976767872", "blocks", "level", "5,", "64k", "chunk,", "algorithm", "2", "[3/3]", "[UUU]"],
    ["md7", ":", "active", "raid1", "sdb1[1]", "sda1[0]"],
    ["104320", "blocks", "[2/2]", "[UU]"],
    ["md8", ":", "active", "raid1", "sdb3[1]", "sda3[0]"],
    ["486239232", "blocks", "[2/2]", "[UU]"],
    ["md9", ":", "active", "(auto-read-only)", "raid1", "sda6[0]", "sdb6[1]"],
    ["4200952", "blocks", "super", "1.0", "[2/2]", "[UU]"],
    ["resync=PENDING"],
    ["bitmap:", "9/9", "pages", "[36KB],", "256KB", "chunk"],
    ["md10", ":", "active", "raid0", "sdb3[0]", "sda3[1]"],
    ["16386048", "blocks", "64k", "chunks"],
    ["md11", ":", "active", "raid1", "sdc3[3]", "sda3[2](F)", "sdb3[1]"],
    ["48837528", "blocks", "super", "1.0", "[2/2]", "[UU]"],
    ["md12", ":", "active", "raid1", "sdc4[3]", "sda4[2](F)", "sdb4[1]"],
    ["193277940", "blocks", "super", "1.0", "[2/2]", "[UU]"],
    ["md13", ":", "active", "raid1", "sdd1[1]", "sdc1[0]"],
    ["10484668", "blocks", "super", "1.1", "[2/2]", "[UU]"],
    ["bitmap:", "1/1", "pages", "[4KB],", "65536KB", "chunk"],
    ["md14", ":", "active", "raid5", "sda3[0]", "sdb3[1]", "sdd3[4]", "sdc3[2]"],
    [
        "11686055424",
        "blocks",
        "super",
        "1.2",
        "level",
        "5,",
        "512k",
        "chunk,",
        "algorithm",
        "2",
        "[4/3]",
        "[UUU_]",
    ],
    [
        "[======>..............]",
        "recovery",
        "=",
        "31.8%",
        "(1241578496/3895351808)",
        "finish=746.8min",
        "speed=59224K/sec",
    ],
    ["md15", ":", "active", "raid1", "sdb1[1]", "sda1[0]"],
    ["10485688", "blocks", "super", "1.0", "[2/2]", "[UU]"],
    ["bitmap:", "0/1", "pages", "[0KB],", "65536KB", "chunk"],
    ["md16", ":", "active", "raid1", "nvme6n1[0]"],
    ["7501333824", "blocks", "super", "1.2", "[1/1]", "[U]"],
    ["bitmap:", "4/56", "pages", "[16KB],", "65536KB", "chunk"],
    ["unused", "devices:", "<none>"],
]

discovery = {
    "": [
        ("md1", None),
        ("md11", None),
        ("md12", None),
        ("md13", None),
        ("md14", None),
        ("md15", None),
        ("md2", None),
        ("md3", None),
        ("md4", None),
        ("md5", None),
        ("md6", None),
        ("md7", None),
        ("md8", None),
        ("md9", None),
        ("md16", None),
    ]
}

checks = {
    "": [
        (
            "md1",
            {},
            [
                (0, "Status: active", []),
                (0, "Spare: 0, Failed: 0, Active: 2", []),
                (0, "Status: 2/2, UU", []),
            ],
        ),
        (
            "md11",
            {},
            [
                (0, "Status: active", []),
                (0, "Spare: 0, Failed: 1, Active: 2", []),
                (0, "Status: 2/2, UU", []),
            ],
        ),
        (
            "md12",
            {},
            [
                (0, "Status: active", []),
                (0, "Spare: 0, Failed: 1, Active: 2", []),
                (0, "Status: 2/2, UU", []),
            ],
        ),
        (
            "md13",
            {},
            [
                (0, "Status: active", []),
                (0, "Spare: 0, Failed: 0, Active: 2", []),
                (0, "Status: 2/2, UU", []),
            ],
        ),
        (
            "md14",
            {},
            [
                (0, "Status: active", []),
                (0, "Spare: 0, Failed: 0, Active: 4", []),
                (2, "Status: 4/3, UUU_", []),
                (1, "[Recovery] 31.8%, Finish: 746.8min, Speed: 59224K/sec", []),
            ],
        ),
        (
            "md15",
            {},
            [
                (0, "Status: active", []),
                (0, "Spare: 0, Failed: 0, Active: 2", []),
                (0, "Status: 2/2, UU", []),
            ],
        ),
        (
            "md2",
            {},
            [
                (0, "Status: active", []),
                (0, "Spare: 0, Failed: 0, Active: 5", []),
                (0, "Status: 5/5, UUUUU", []),
                (0, "[Check] Finish: 255.8min, Speed: 122145K/sec, Status: 76.0%", []),
            ],
        ),
        (
            "md3",
            {},
            [
                (0, "Status: active", []),
                (0, "Spare: 0, Failed: 0, Active: 2", []),
                (0, "Status: 2/2, UU", []),
            ],
        ),
        (
            "md4",
            {},
            [
                (0, "Status: active", []),
                (0, "Spare: 0, Failed: 0, Active: 2", []),
                (0, "Status: 2/2, UU", []),
            ],
        ),
        (
            "md5",
            {},
            [
                (0, "Status: active(auto-read-only)", []),
                (0, "Spare: 0, Failed: 0, Active: 2", []),
                (0, "Status: 2/2, UU", []),
            ],
        ),
        (
            "md6",
            {},
            [
                (0, "Status: active", []),
                (0, "Spare: 1, Failed: 0, Active: 3", []),
                (0, "Status: 3/3, UUU", []),
            ],
        ),
        (
            "md7",
            {},
            [
                (0, "Status: active", []),
                (0, "Spare: 0, Failed: 0, Active: 2", []),
                (0, "Status: 2/2, UU", []),
            ],
        ),
        (
            "md8",
            {},
            [
                (0, "Status: active", []),
                (0, "Spare: 0, Failed: 0, Active: 2", []),
                (0, "Status: 2/2, UU", []),
            ],
        ),
        (
            "md9",
            {},
            [
                (0, "Status: active(auto-read-only)", []),
                (0, "Spare: 0, Failed: 0, Active: 2", []),
                (0, "Status: 2/2, UU", []),
                (1, "[Resync] Status: PENDING", []),
            ],
        ),
        (
            "md16",
            {},
            [
                (0, "Status: active", []),
                (0, "Spare: 0, Failed: 0, Active: 1", []),
                (0, "Status: 1/1, U", []),
            ],
        ),
    ]
}
